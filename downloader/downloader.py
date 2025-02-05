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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': 'application/json',
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
        self.download_mode = mode
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.rate_limit = Semaphore(max_workers)
    
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
            max_retries = self.max_retries  # Usar el valor global si no se especifica

        domain = urlparse(url).netloc
        retry_wait = 1

        for attempt in range(max_retries):
            if self.cancel_requested.is_set():
                return None

            with self.domain_locks[domain]:
                # Respetar el intervalo de tiempo para este dominio
                elapsed_time = time.time() - self.domain_last_request[domain]
                if elapsed_time < self.rate_limit_interval:
                    time.sleep(self.rate_limit_interval - elapsed_time)

                try:
                    with self.rate_limit:
                        response = self.session.get(url, stream=True, headers=self.headers)
                    response.raise_for_status()
                    self.domain_last_request[domain] = time.time()  # Actualizar la hora de la última solicitud
                    return response

                except requests.exceptions.RequestException as e:
                    # Si el error es 429 o 5xx se reintenta; de lo contrario se aborta
                    status_code = getattr(e.response, 'status_code', None)
                    if status_code in (429, 500, 502, 503, 504):
                        self.log(f"Intento {attempt + 1}/{max_retries}: Reintentando después del error {status_code} para la URL: {url}")
                        time.sleep(self.retry_interval)  # Intervalo definido por el usuario
                        retry_wait *= 2
                    else:
                        self.log(f"Error no reintentable para la URL: {url} - {e}")
                        break

        self.log(f"Se excedieron los reintentos máximos ({max_retries}) para la URL: {url}")
        return None

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
                with self.rate_limit:
                    response = self.session.get(api_url, headers=self.headers)
                response.raise_for_status()
                posts = response.json()
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

    def get_filename(self, media_url, post_id=None, post_name=None):
        base_name = os.path.basename(media_url).split('?')[0]
        extension = os.path.splitext(base_name)[1]
        if not hasattr(self, 'file_naming_mode'):
            self.file_naming_mode = 0
        mode = self.file_naming_mode

        # DEBUG
        #self.log(f"DEBUG -> mode={mode}, post_name='{post_name}', post_id='{post_id}', base_name='{base_name}'")

        if mode == 0:
            final_name = self.sanitize_filename(base_name)
        elif mode == 1:
            final_name = f"{self.sanitize_filename(post_name or 'post')}{extension}"
        elif mode == 2:
            final_name = f"{self.sanitize_filename(post_name or 'post')} - {post_id}{extension}"
        else:
            final_name = self.sanitize_filename(base_name)

        #self.log(f"DEBUG -> final_name='{final_name}'")
        return final_name

    def process_post(self, post):
        media_urls = []
        if 'file' in post and post['file']:
            file_url = urljoin("https://coomer.su/", post['file']['path'])
            media_urls.append(file_url)
        if 'attachments' in post and post['attachments']:
            for attachment in post['attachments']:
                attachment_url = urljoin("https://coomer.su/", attachment['path'])
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

    def process_media_element(self, media_url, user_id, post_id=None, post_name=None):

        if self.cancel_requested.is_set():
            return

        # Determinar la extensión
        extension = os.path.splitext(media_url)[1].lower()
        if (extension in self.image_extensions and not self.download_images) or \
        (extension in self.video_extensions and not self.download_videos) or \
        (extension in self.compressed_extensions and not self.download_compressed):
            self.log(self.tr("Skipping {media_url} due to download settings.", media_url=media_url))
            return

        self.log(self.tr("Starting download from {media_url}", media_url=media_url))

        # Determinar el nombre final usando get_filename; se debe haber actualizado file_naming_mode
        filename = self.get_filename(media_url, post_id=post_id, post_name=post_name)
        media_folder = self.get_media_folder(extension, user_id, post_id)
        os.makedirs(media_folder, exist_ok=True)

        final_path = os.path.normpath(os.path.join(media_folder, filename))
        tmp_path = final_path + ".tmp"  # Archivo temporal

        # Si existe un archivo temporal incompleto, eliminarlo
        if os.path.exists(tmp_path):
            self.log(self.tr("Removing incomplete file: {tmp_path}", tmp_path=tmp_path))
            os.remove(tmp_path)

        # Revisar en la base de datos para evitar volver a descargar el mismo archivo
        if media_url in self.download_cache:
            self.log(self.tr("File already exists in DB, skipping: {final_path}", final_path=final_path))
            self.skipped_files.append(final_path)
            return

        try:
            response = self.safe_request(media_url)
            if response is None:
                self.log(self.tr("Failed to download after multiple retries: {media_url}", media_url=media_url))
                self.failed_files.append(media_url)
                return

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            self.start_time = time.time()

            with open(tmp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1048576):
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(tmp_path)
                        self.log(self.tr("Download cancelled from {media_url}", media_url=media_url))
                        return

                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # Calcular velocidad y tiempo restante
                    elapsed_time = time.time() - self.start_time
                    speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                    remaining_time = (total_size - downloaded_size) / speed if speed > 0 else 0

                    if self.update_progress_callback:
                        self.update_progress_callback(
                            downloaded_size, total_size,
                            file_id=media_url,
                            file_path=tmp_path,
                            speed=speed,
                            eta=remaining_time
                        )

            # Si la descarga se completó, renombrar el archivo temporal al nombre final
            os.rename(tmp_path, final_path)

            self.completed_files += 1
            self.log(self.tr("Download success from {media_url}", media_url=media_url))
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)

            # Insertar el registro en la base de datos
            with self.db_lock:
                self.db_cursor.execute(
                    """INSERT OR REPLACE INTO downloads (media_url, file_path, file_size, user_id, post_id)
                    VALUES (?, ?, ?, ?, ?)""",
                    (media_url, final_path, total_size, user_id, post_id)
                )
                self.db_connection.commit()

            # Actualizar la caché local
            self.download_cache[media_url] = (final_path, total_size)

        except Exception as e:
            self.log(self.tr("Error downloading: {e}", e=e))
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            self.failed_files.append(media_url)

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

            futures = []
            self.total_files = 0  # se recalculará

            # Recorremos cada post
            for post in posts:
                current_post_id = post.get('id') or "unknown_id"
                # Tomamos el 'title' del post para usarlo como post_name
                title = post.get('title') or ""

                # Obtenemos la lista de URLs de archivos para este post
                media_urls = self.process_post(post)

                # Filtramos según extensiones (se puede omitir, pues ya está en process_post si quieres)
                for media_url in media_urls:
                    extension = os.path.splitext(media_url)[1].lower()
                    if (extension in self.image_extensions and not self.download_images) or \
                    (extension in self.video_extensions and not self.download_videos) or \
                    (extension in self.compressed_extensions and not self.download_compressed):
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
                    extension = os.path.splitext(media_url)[1].lower()
                    if (extension in self.image_extensions and not self.download_images) or \
                    (extension in self.video_extensions and not self.download_videos) or \
                    (extension in self.compressed_extensions and not self.download_compressed):
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
                            title  # <-- pasamos el título aquí
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
                    self.process_media_element(media_url, user_id)
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

