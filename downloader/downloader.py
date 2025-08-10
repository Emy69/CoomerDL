from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from urllib.parse import quote_plus, urlencode, urljoin, urlparse
import os
import re
import requests
import threading
import time
import sqlite3

class Downloader:
    def __init__(self, download_folder, max_workers=5, log_callback=None, 
                 enable_widgets_callback=None, update_progress_callback=None, 
                 update_global_progress_callback=None, headers=None,
                 max_retries=3, retry_interval=2.0,
                 download_images=True, download_videos=True, download_compressed=True, 
                 tr=None, folder_structure='default', rate_limit_interval=2.0):
        
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.cancel_requested = threading.Event()  # Para manejar cancelaciones
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Referer': 'https://coomer.st/',
        }
        self.media_counter = 0
        self.session = requests.Session()
        self.max_workers = max_workers  # Número máximo de hilos concurrentes
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.rate_limit = Semaphore(self.max_workers)  # Limita el número de peticiones concurrentes
        self.domain_locks = defaultdict(lambda: Semaphore(2))
        self.domain_last_request = defaultdict(float)  # Última solicitud por dominio
        self.rate_limit_interval = rate_limit_interval
        self.download_mode = "multi"  # Modo de descarga: 'multi' para concurrente, 'queue' para secuencial
        self.video_extensions = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv', '.m4v')
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        self.document_extensions = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')
        self.compressed_extensions = ('.zip', '.rar', '.7z', '.tar', '.gz')
        self.download_images = download_images
        self.download_videos = download_videos
        self.download_compressed = download_compressed
        self.futures = []  # Lista para almacenar los objetos Future de tareas concurrentes
        self.total_files = 0
        self.completed_files = 0
        self.skipped_files = []  
        self.failed_files = []
        self.start_time = None
        self.tr = tr
        self.shutdown_called = False  # Para evitar múltiples cierres del executor
        self.folder_structure = folder_structure
        self.failed_retry_count = {}
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.file_lock = threading.Lock()
        self.post_attachment_counter = defaultdict(int)
        self.subdomain_cache = {}
        self.subdomain_locks = defaultdict(threading.Lock)

        
        # ----- NUEVA SECCIÓN: INICIALIZACIÓN DE LA BASE DE DATOS -----
        db_folder = os.path.join("resources", "config")
        os.makedirs(db_folder, exist_ok=True)  # Se asegura que la carpeta exista
        self.db_path = os.path.join(db_folder, "downloads.db")
        self.db_lock = threading.Lock()  # Lock para operaciones en la DB
        self.init_db()
        self.load_download_cache()
        # --------------------------------------------------------------

    def init_db(self):
        """Inicializa (o crea si no existe) la base de datos para registrar los archivos descargados."""
        self.db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_url TEXT UNIQUE,
                file_path TEXT,
                file_size INTEGER,
                user_id TEXT,
                post_id TEXT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db_connection.commit()

    def load_download_cache(self):
        """Carga todos los registros de la DB en un diccionario para búsquedas rápidas."""
        with self.db_lock:
            self.db_cursor.execute("SELECT media_url, file_path, file_size FROM downloads")
            rows = self.db_cursor.fetchall()
        # La cache se estructura como: { media_url: (file_path, file_size), ... }
        self.download_cache = {row[0]: (row[1], row[2]) for row in rows}


    def log(self, message):
        if self.log_callback:
            self.log_callback(self.tr(message) if self.tr else message)

    def set_download_mode(self, mode, max_workers):
        """
        Actualiza dinámicamente el modo de descarga ('multi' o 'queue') y 
        el número máximo de threads (max_workers).
        Si el modo es 'queue', forzamos max_workers=1 para no tener concurrencia.
        """
        if mode == 'queue':
            max_workers = 1  # Forzar a 1 hilo en modo cola
        
        self.download_mode = mode
        self.max_workers = max_workers

        # Cerrar el executor anterior
        if self.executor:
            self.executor.shutdown(wait=True)

        # Crear un nuevo ThreadPoolExecutor y un nuevo Semaphore
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.rate_limit = Semaphore(max_workers)

        self.log(f"Updated download mode to {mode} with max_workers = {max_workers}")
    
    def set_retry_settings(self, max_retries, retry_interval):
        self.max_retries = max_retries
        self.rate_limit_interval = retry_interval 

    def request_cancel(self):
        self.cancel_requested.set()
        self.log(self.tr("Download cancellation requested."))
        for future in self.futures:
            future.cancel()

    def shutdown_executor(self):
        if not self.shutdown_called:
            self.shutdown_called = True
            if self.executor:
                self.executor.shutdown(wait=True)
            if self.enable_widgets_callback:
                self.enable_widgets_callback()
            self.log(self.tr("All downloads completed or cancelled."))

    def safe_request(self, url, max_retries=None):
        if max_retries is None:
            max_retries = self.max_retries

        domain = urlparse(url).netloc
        path = urlparse(url).path
        retry_wait = 1

        for attempt in range(max_retries):
            if self.cancel_requested.is_set():
                return None

            with self.domain_locks[domain]:
                elapsed_time = time.time() - self.domain_last_request[domain]
                if elapsed_time < self.rate_limit_interval:
                    time.sleep(self.rate_limit_interval - elapsed_time)

                try:
                    response = self.session.get(url, stream=True, headers=self.headers)
                    if response.status_code == 403 and "coomer.st" in url:
                        # Aviso inicial
                        if self.update_progress_callback:
                            self.update_progress_callback(0, 0, status="403")

                        # Buscar subdominio alternativo
                        with self.subdomain_locks[path]:
                            if path in self.subdomain_cache:
                                alt_url = self.subdomain_cache[path]
                            else:
                                alt_url = self._find_valid_subdomain(url)
                                self.subdomain_cache[path] = alt_url

                        if alt_url != url:
                            # Aviso: subdominio encontrado
                            found = urlparse(alt_url).netloc
                            if self.update_progress_callback:
                                self.update_progress_callback(
                                    0, 0, status=f"Subdomain found: {found}"
                                )

                            response = self.session.get(alt_url, stream=True,
                                                        headers=self.headers)
                            response.raise_for_status()
                            return response
                        else:
                            # Todos fallaron
                            if self.update_progress_callback:
                                self.update_progress_callback(0, 0, status="Exhausted subdomains")
                            return None

                    response.raise_for_status()
                    return response

                except requests.exceptions.RequestException as e:
                    status_code = getattr(e.response, 'status_code', None)
                    if status_code in (429, 500, 502, 503, 504):
                        self.log(self.tr("Intento {attempt}/{max_retries}: Error {status_code} - Reintentando...").format(
                            attempt=attempt + 1, max_retries=max_retries, status_code=status_code))
                        time.sleep(retry_wait)
                        retry_wait *= 2
                    else:
                        url_display = getattr(e.request, 'url', url)
                        if len(url_display) > 60:
                            url_display = url_display[:60] + "..."
                        self.log(self.tr("Intento {attempt}/{max_retries}: Error al acceder a {url} - {error}").format(
                            attempt=attempt + 1, max_retries=max_retries, url=url_display, error=e))
                        if attempt < max_retries - 1:
                            time.sleep(self.retry_interval)

        return None

    def _find_valid_subdomain(self, url, max_subdomains=10):
        parsed = urlparse(url)
        path = parsed.path if parsed.path.startswith("/data/") else f"/data{parsed.path}"

        for i in range(1, max_subdomains + 1):
            domain = f"n{i}.coomer.st"
            test_url = parsed._replace(netloc=domain, path=path).geturl()

            # Aviso: probando
            if self.update_progress_callback:
                self.update_progress_callback(0, 0, status=f"Testing subdomain: {domain}")

            try:
                resp = self.session.get(test_url, headers=self.headers,
                                        timeout=15, stream=True)
                if resp.status_code == 200:
                    # OK → la llamada que recibe safe_request mostrará “encontrado”
                    return test_url
                else:
                    if self.update_progress_callback:
                        self.update_progress_callback(
                            0, 0, status=f"Invalid subdomain: {domain}"
                        )
            except requests.exceptions.ReadTimeout:
                if self.update_progress_callback:
                    self.update_progress_callback(
                        0, 0, status=f"Timeout in: {domain}"
                    )
            except Exception:
                if self.update_progress_callback:
                    self.update_progress_callback(
                        0, 0, status=f"Invalid subdomain: {domain}"
                    )

        return url

    def fetch_user_posts(self, site, user_id, service, query=None, specific_post_id=None, initial_offset=0, log_fetching=True):
        all_posts = []
        offset = initial_offset
        user_id_encoded = quote_plus(user_id)
        while True:
            if self.cancel_requested.is_set():
                return all_posts

            api_url = f"https://{site}/api/v1/{service}/user/{user_id_encoded}"
            url_query = {"o": offset}
            if query is not None:
                url_query["q"] = query
            api_url += "?" + urlencode(url_query)
            if log_fetching:
                self.log(self.tr("Fetching user posts from {api_url}", api_url=api_url))
            try:
                # Para la llamada a la API no usamos stream
                response = self.session.get(api_url, headers=self.headers)
                response.raise_for_status()
                try:
                    posts_data = response.json()
                except ValueError as e:
                    self.log(self.tr("Error al parsear JSON: {e}", e=e))
                    break
                # Si la respuesta es un diccionario y tiene la clave 'data', se usa esa lista
                if isinstance(posts_data, dict) and 'data' in posts_data:
                    posts = posts_data['data']
                else:
                    posts = posts_data
                if not posts:
                    break
                if specific_post_id:
                    post = next((p for p in posts if p['id'] == specific_post_id), None)
                    if post:
                        return [post]
                all_posts.extend(posts)
                offset += 50
            except Exception as e:
                self.log(self.tr("Error fetching user posts: {e}", e=e))
                break
        if specific_post_id:
            return [post for post in all_posts if post['id'] == specific_post_id]
        return all_posts


    def get_filename(self, media_url, post_id=None, post_name=None, attachment_index=1):
        base_name = os.path.basename(media_url).split('?')[0]
        name_no_ext, extension = os.path.splitext(base_name)
        if not hasattr(self, 'file_naming_mode'):
            self.file_naming_mode = 0
        mode = self.file_naming_mode

        def sanitize(name):
            # Only remove forbidden characters; Unicode letters (e.g. Hiragana, Kanji) remain intact.
            sanitized = self.sanitize_filename(name)
            return sanitized.strip()

        if mode == 0:
            # Use original file name (File ID)
            sanitized = sanitize(name_no_ext)
            if not sanitized:
                sanitized = "file"  # fallback default if needed
            final_name = f"{sanitized}_{attachment_index}{extension}"
        elif mode == 1:
            # Use post name
            sanitized_post = sanitize(post_name or "")
            if not sanitized_post:
                sanitized_post = f"post_{post_id}" if post_id else "post"
            short_hash = f"{hash(media_url) & 0xFFFF:04x}"
            final_name = f"{sanitized_post}_{attachment_index}_{short_hash}{extension}"
        elif mode == 2:
            # Use post name and post ID
            sanitized_post = sanitize(post_name or "")
            if not sanitized_post:
                sanitized_post = f"post_{post_id}" if post_id else "post"
            if post_id:
                final_name = f"{sanitized_post} - {post_id}_{attachment_index}{extension}"
            else:
                final_name = f"{sanitized_post}_{attachment_index}{extension}"
        else:
            final_name = sanitize(name_no_ext) + extension

        return final_name



    def process_post(self, post):
        media_urls = []
        if 'file' in post and post['file']:
            file_url = urljoin("https://coomer.st/", post['file']['path'])
            media_urls.append(file_url)
        if 'attachments' in post and post['attachments']:
            for attachment in post['attachments']:
                attachment_url = urljoin("https://coomer.st/", attachment['path'])
                media_urls.append(attachment_url)
        return media_urls

    def sanitize_filename(self, filename):
        return re.sub(r'[<>:"/\\|?*]', '_', filename)

    def get_media_folder(self, extension, user_id, post_id=None):
        if extension in self.video_extensions:
            folder_name = "videos"
        elif extension in self.image_extensions:
            folder_name = "images"
        elif extension in self.document_extensions:
            folder_name = "documents"
        elif extension in self.compressed_extensions:
            folder_name = "compressed"
        else:
            folder_name = "other"
        if self.folder_structure == 'post_number' and post_id:
            media_folder = os.path.join(self.download_folder, user_id, f'post_{post_id}', folder_name)
        else:
            media_folder = os.path.join(self.download_folder, user_id, folder_name)
        return media_folder

    def process_media_element(self, media_url, user_id, post_id=None,
                          post_name=None, download_id=None):
    # Si se ha solicitado cancelar, se aborta.
        if self.cancel_requested.is_set():
            return

        extension = os.path.splitext(media_url)[1].lower()
        if (extension in self.image_extensions and not self.download_images) or \
        (extension in self.video_extensions and not self.download_videos) or \
        (extension in self.compressed_extensions and not self.download_compressed):
            self.log(f"Skipping {media_url} due to settings.")
            return

        self.log(f"Starting download from {media_url}")

        # Actualizar contador para numerar archivos adjuntos
        if post_id:
            self.post_attachment_counter[post_id] += 1
            attachment_index = self.post_attachment_counter[post_id]
        else:
            attachment_index = 1

        filename = self.get_filename(media_url, post_id=post_id, post_name=post_name,
                                    attachment_index=attachment_index)
        media_folder = self.get_media_folder(extension, user_id, post_id)
        os.makedirs(media_folder, exist_ok=True)

        final_path = os.path.normpath(os.path.join(media_folder, filename))
        tmp_path = final_path + ".tmp"

        # Si el archivo ya figura en la DB, se omite la descarga.
        if media_url in self.download_cache:
            self.log(f"File from {media_url} is in DB, skipping.")
            self.skipped_files.append(final_path)
            return

        response = self.safe_request(media_url, max_retries=self.max_retries)
        if response is None:
            self.log(f"Failed to download {media_url} after retries.")
            self.failed_files.append(media_url)
            return

        try:
            total_size = int(response.headers.get('content-length', 0))
        except Exception as e:
            self.log(f"Error getting total size: {e}")
            total_size = 0

        downloaded_size = 0
        self.start_time = time.time()

        # Abrir el archivo temporal para escribir los primeros chunks.
        with open(tmp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1048576):
                if self.cancel_requested.is_set():
                    f.close()
                    os.remove(tmp_path)
                    self.log(f"Download cancelled from {media_url}")
                    return
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if self.update_progress_callback:
                        elapsed_time = time.time() - self.start_time
                        speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                        remaining_time = (total_size - downloaded_size) / speed if speed > 0 else 0
                        self.update_progress_callback(downloaded_size, total_size,
                                                    file_id=download_id,
                                                    file_path=tmp_path,
                                                    speed=speed,
                                                    eta=remaining_time)

        # Si no se ha descargado el total esperado, reanudar la descarga
        while total_size and downloaded_size < total_size:
            # Prepara cabecera para reanudar la descarga
            resume_headers = self.headers.copy()
            resume_headers['Range'] = f'bytes={downloaded_size}-'
            self.log(f"Resuming download at byte {downloaded_size} for {media_url}")
            part_response = self.session.get(media_url, stream=True, headers=resume_headers, timeout=30)
            part_response.raise_for_status()

            with open(tmp_path, 'ab') as f:
                for chunk in part_response.iter_content(chunk_size=1048576):
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(tmp_path)
                        self.log(f"Download cancelled from {media_url}")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if self.update_progress_callback:
                            elapsed_time = time.time() - self.start_time
                            speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                            remaining_time = (total_size - downloaded_size) / speed if speed > 0 else 0
                            self.update_progress_callback(downloaded_size, total_size,
                                                        file_id=download_id,
                                                        file_path=tmp_path,
                                                        speed=speed,
                                                        eta=remaining_time)

        # Una vez completada la descarga, renombrar el archivo.
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(tmp_path, final_path)

        self.completed_files += 1
        self.log(f"Download success from {media_url}")
        if self.update_global_progress_callback:
            self.update_global_progress_callback(self.completed_files, self.total_files)

        # Registrar el archivo en la base de datos.
        with self.db_lock:
            self.db_cursor.execute(
                """INSERT OR REPLACE INTO downloads (media_url, file_path, file_size, user_id, post_id)
                VALUES (?, ?, ?, ?, ?)""",
                (media_url, final_path, total_size, user_id, post_id)
            )
            self.db_connection.commit()

        self.download_cache[media_url] = (final_path, total_size)




    def get_remote_file_size(self, media_url, filename):
        try:
            response = requests.head(media_url, allow_redirects=True)
            if response.status_code == 200:
                size = int(response.headers.get('Content-Length', 0))
                return media_url, filename, size
            else:
                self.log(self.tr(f"Failed to get size for {filename}: HTTP {response.status_code}"))
                return media_url, filename, None
        except Exception as e:
            self.log(self.tr(f"Error getting size for {filename}: {e}"))
            return media_url, filename, None

    def download_media(self, site, user_id, service, query=None, download_all=False, initial_offset=0):
        try:
            self.log(self.tr("Starting download process..."))

            posts = self.fetch_user_posts(
                site, user_id, service,
                query=query,
                initial_offset=initial_offset,
                log_fetching=download_all
            )
            if not posts:
                self.log(self.tr("No posts found for this user."))
                return

            if not download_all:
                # Limita a los primeros 50 posts si no es "download all"
                posts = posts[:50]

            self.total_files = 0
            for post in posts:
                current_post_id = post.get('id') or "unknown_id"
                # Tomamos el 'title' del post para usarlo como post_name
                title = post.get('title') or ""

                # Obtenemos la lista de URLs de archivos para este post
                media_urls = self.process_post(post)


                for media_url in media_urls:
                    ext = os.path.splitext(media_url)[1].lower()
                    if (ext in self.image_extensions and not self.download_images) or \
                       (ext in self.video_extensions and not self.download_videos) or \
                       (ext in self.compressed_extensions and not self.download_compressed):
                        continue

                    # Aumentamos total_files
                    self.total_files += 1

            # Segunda pasada, ya sabiendo cuántos archivos totales
            # (Para el "progress" si así lo requieres)
            futures = []
            for post in posts:
                current_post_id = post.get('id') or "unknown_id"
                title = post.get('title') or ""

                media_urls = self.process_post(post)
                for media_url in media_urls:
                    ext = os.path.splitext(media_url)[1].lower()
                    if (ext in self.image_extensions and not self.download_images) or \
                       (ext in self.video_extensions and not self.download_videos) or \
                       (ext in self.compressed_extensions and not self.download_compressed):
                        continue

                    # Dependiendo del modo, encolamos o hacemos en serie
                    if self.download_mode == 'queue':
                        # Llamada directa y secuencial
                        self.process_media_element(
                            media_url,
                            user_id,
                            post_id=current_post_id,
                            post_name=title  
                        )
                    else:
                        # Modo multi (threaded)
                        future = self.executor.submit(
                            self.process_media_element,
                            media_url,
                            user_id,
                            current_post_id,
                            title,  # <-- pasamos el título aquí
                            media_url 
                        )
                        futures.append(future)

            # Espera a que terminen los hilos (si es multi)
            if self.download_mode == 'multi':
                for future in as_completed(futures):
                    if self.cancel_requested.is_set():
                        break

            # Intentamos re-descargar fallidos, si deseas
            if self.failed_files:
                self.log(self.tr("Retrying failed downloads..."))
                for media_url in self.failed_files:
                    if self.cancel_requested.is_set():
                        break
                    self.process_media_element(
                        media_url,
                        user_id,
                        download_id=media_url
                    )
                self.failed_files.clear()

        except Exception as e:
            self.log(self.tr(f"Error during download: {e}"))
        finally:
            self.shutdown_executor()

    def download_single_post(self, site, post_id, service, user_id):
        try:
            post = self.fetch_user_posts(site, user_id, service, specific_post_id=post_id)
            if not post:
                self.log(self.tr("No post found for this ID."))
                return
            media_urls = self.process_post(post[0])
            futures = []
            grouped_media_urls = defaultdict(list)
            for media_url in media_urls:
                grouped_media_urls[post[0]['id']].append(media_url)
            self.total_files = len(media_urls)
            self.completed_files = 0
            for post_id, media_urls in grouped_media_urls.items():
                for media_url in media_urls:
                    if self.download_mode == 'queue':
                        self.process_media_element(media_url, user_id, post_id)
                    else:
                        future = self.executor.submit(self.process_media_element, media_url, user_id, post_id)
                        futures.append(future)
            if self.download_mode == 'multi':
                for future in as_completed(futures):
                    if self.cancel_requested.is_set():
                        break
            if self.failed_files:
                self.log(self.tr("Retrying failed downloads..."))
                for media_url in self.failed_files:
                    if self.cancel_requested.is_set():
                        break
                    self.process_media_element(media_url, user_id)
                self.failed_files.clear()
        except Exception as e:
            self.log(self.tr(f"Error during download: {e}"))
        finally:
            self.shutdown_executor()
    
    def fetch_single_post(self, site, post_id, service):
        api_url = f"https://{site}.su/api/v1/{service}/post/{post_id}"
        self.log(self.tr(f"Fetching post from {api_url}"))
        try:
            with self.rate_limit:
                response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(self.tr(f"Error fetching post: {e}"))
            return None

    def clear_database(self):
        """Borra todos los registros de la base de datos."""
        with self.db_lock:
            self.db_cursor.execute("DELETE FROM downloads")
            self.db_connection.commit()
        self.log(self.tr("Database cleared."))
    
    def update_max_downloads(self, new_max):
        """
        Dynamically updates the number of max workers (threads) for this Downloader.
        Recreates the ThreadPoolExecutor and the rate_limit Semaphore.
        """
        # shut down the old executor safely
        if self.executor:
            self.executor.shutdown(wait=True)

        self.max_workers = new_max
        self.executor = ThreadPoolExecutor(max_workers=new_max)
        self.rate_limit = Semaphore(new_max)

        self.log(f"Updated max_workers to {new_max}")

