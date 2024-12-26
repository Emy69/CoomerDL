from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock, Event
from urllib.parse import quote_plus, urlencode, urljoin, urlparse
import os
import re
import requests
import threading
import time
from typing import Optional, Callable, List, Dict, Tuple

class Downloader:
    def __init__(
        self,
        download_folder: str,
        max_workers: int = 5,
        log_callback: Optional[Callable[[str], None]] = None,
        enable_widgets_callback: Optional[Callable[[], None]] = None,
        update_progress_callback: Optional[Callable[[int, int, Optional[str], Optional[str], Optional[float], Optional[float]], None]] = None,
        update_global_progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None,
        download_images: bool = True,
        download_videos: bool = True,
        download_compressed: bool = True,
        tr: Optional[Callable[[str], str]] = None,
        folder_structure: str = 'default',
        rate_limit_interval: float = 2.0
    ):
        """
        Inicializa el descargador con las configuraciones proporcionadas.
        """
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.cancel_requested = Event()  # Event to handle cancellation requests
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        self.media_counter = 0
        self.session = requests.Session()
        self.max_workers = max_workers  # Maximum number of concurrent threads
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.rate_limit = Semaphore(self.max_workers)  # Semaphore to limit the number of concurrent requests
        self.domain_locks = defaultdict(lambda: Semaphore(2))
        self.domain_last_request = defaultdict(float)  # Tracks last request time per domain
        self.rate_limit_interval = rate_limit_interval
        self.download_mode = "multi"  # 'multi' for concurrent, 'queue' for sequential
        self.video_extensions = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv', '.m4v'}
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        self.document_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
        self.compressed_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz'}
        self.download_images = download_images
        self.download_videos = download_videos
        self.download_compressed = download_compressed
        self.futures: List = []  # List to keep track of future objects
        self.total_files = 0
        self.completed_files = 0
        self.skipped_files: List[str] = []  
        self.failed_files: List[str] = []
        self.start_time: Optional[float] = None
        self.tr = tr
        self.shutdown_called = False  # Flag to prevent multiple shutdowns
        self.folder_structure = folder_structure
        self.failed_retry_count: Dict[str, int] = {}
        self.lock = Lock()  # Lock to protect shared resources

    def log(self, message: str):
        """
        Llama al callback de log con el mensaje proporcionado.
        """
        if self.log_callback:
            translated_message = self.tr(message) if self.tr else message
            self.log_callback(translated_message)

    def set_download_mode(self, mode: str, max_workers: int):
        """
        Establece el modo de descarga y actualiza el número de trabajadores.
        """
        if mode not in ['multi', 'queue']:
            self.log(f"Invalid download mode: {mode}")
            return
        self.download_mode = mode
        with self.lock:
            self.max_workers = max_workers
            # Recreate executor and rate limit semaphore
            self.executor.shutdown(wait=False)
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self.rate_limit = Semaphore(self.max_workers)

    def request_cancel(self):
        """
        Solicita la cancelación de todas las descargas en curso.
        """
        self.cancel_requested.set()
        self.log(self.tr("Download cancellation requested.") if self.tr else "Download cancellation requested.")
        with self.lock:
            for future in self.futures:
                future.cancel()

    def shutdown_executor(self):
        """
        Cierra el ThreadPoolExecutor de manera segura.
        """
        if not self.shutdown_called:
            self.shutdown_called = True
            self.executor.shutdown(wait=True)
            if self.enable_widgets_callback:
                self.enable_widgets_callback()
            self.log(self.tr("All downloads completed or cancelled.") if self.tr else "All downloads completed or cancelled.")

    def safe_request(self, url: str, max_retries: int = 5) -> Optional[requests.Response]:
        """
        Realiza una solicitud HTTP GET con reintentos y limitación de tasa.
        """
        retry_wait = 1
        domain = urlparse(url).netloc

        for attempt in range(max_retries):
            if self.cancel_requested.is_set():
                self.log(self.tr("Download cancelled.") if self.tr else "Download cancelled.")
                return None

            with self.domain_locks[domain]:
                # Rate limiting per domain
                last_request = self.domain_last_request[domain]
                elapsed_time = time.time() - last_request
                if elapsed_time < self.rate_limit_interval:
                    time.sleep(self.rate_limit_interval - elapsed_time)

                try:
                    with self.rate_limit:
                        response = self.session.get(url, stream=True, headers=self.headers, timeout=10)
                    response.raise_for_status()
                    self.domain_last_request[domain] = time.time()
                    return response

                except requests.exceptions.RequestException as e:
                    if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                        self.log(f"Retry {attempt + 1}: Error 429 Too Many Requests for URL: {url}. Retrying in {retry_wait} seconds.")
                        time.sleep(retry_wait)
                        retry_wait *= 2  # Exponential backoff
                    else:
                        self.log(f"Non-retryable error: {e} for URL: {url}.")
                        break

        self.log(f"Failed to retrieve URL after {max_retries} attempts: {url}")
        return None

    def fetch_user_posts(
        self, 
        site: str, 
        user_id: str, 
        service: str, 
        query: Optional[str] = None, 
        specific_post_id: Optional[str] = None, 
        initial_offset: int = 0, 
        log_fetching: bool = True
    ) -> List[Dict]:
        """
        Obtiene todas las publicaciones de un usuario desde la API.
        """
        all_posts = []
        offset = initial_offset
        user_id_encoded = quote_plus(user_id)

        while True:
            if self.cancel_requested.is_set():
                return all_posts

            api_url = f"https://{site}/api/v1/{service}/user/{user_id_encoded}"
            url_query = {"o": offset}
            if query:
                url_query["q"] = query

            full_api_url = f"{api_url}?{urlencode(url_query)}"

            if log_fetching:
                self.log(self.tr("Fetching user posts from {api_url}", api_url=full_api_url) if self.tr else f"Fetching user posts from {full_api_url}")

            response = self.safe_request(full_api_url)
            if response is None:
                break

            try:
                posts = response.json()
                if not posts:
                    break

                if specific_post_id:
                    post = next((p for p in posts if p['id'] == specific_post_id), None)
                    if post:
                        return [post]

                all_posts.extend(posts)
                offset += 50  # Asumiendo que la API devuelve 50 posts por solicitud

            except ValueError as e:
                self.log(self.tr("Error parsing JSON response: {e}", e=e) if self.tr else f"Error parsing JSON response: {e}")
                break

        if specific_post_id:
            return [post for post in all_posts if post['id'] == specific_post_id]
        return all_posts

    def process_post(self, post: Dict) -> List[str]:
        """
        Extrae las URLs de medios de una publicación.
        """
        media_urls = []

        # Extraer el archivo principal
        file_url = post.get('file', {}).get('path')
        if file_url:
            full_file_url = urljoin("https://coomer.su/", file_url)
            media_urls.append(full_file_url)

        # Extraer los archivos adjuntos
        attachments = post.get('attachments', [])
        for attachment in attachments:
            attachment_url = attachment.get('path')
            if attachment_url:
                full_attachment_url = urljoin("https://coomer.su/", attachment_url)
                media_urls.append(full_attachment_url)

        return media_urls

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza el nombre del archivo reemplazando caracteres no válidos.
        """
        return re.sub(r'[<>:"/\\|?*]', '_', filename)

    def get_media_folder(self, extension: str, user_id: str, post_id: Optional[str] = None) -> str:
        """
        Determina la carpeta de destino para el archivo basado en su extensión.
        """
        extension = extension.lower()
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

    def process_media_element(self, media_url: str, user_id: str, post_id: Optional[str] = None):
        """
        Descarga un elemento de media (imagen, video, etc.).
        """
        extension = os.path.splitext(media_url)[1].lower()
        if self.cancel_requested.is_set():
            return

        # Verificar si el tipo de archivo debe ser descargado
        if (extension in self.image_extensions and not self.download_images) or \
           (extension in self.video_extensions and not self.download_videos) or \
           (extension in self.compressed_extensions and not self.download_compressed):
            self.log(self.tr("Skipping {media_url} due to download settings.", media_url=media_url) if self.tr else f"Skipping {media_url} due to download settings.")
            return

        self.log(self.tr("Starting download from {media_url}", media_url=media_url) if self.tr else f"Starting download from {media_url}")

        try:
            response = self.safe_request(media_url)
            if response is None:
                self.increment_failed_files(media_url)
                return

            media_folder = self.get_media_folder(extension, user_id, post_id)
            os.makedirs(media_folder, exist_ok=True)

            filename = os.path.basename(urlparse(media_url).path).split('?')[0]
            filename = self.sanitize_filename(filename)
            filepath = os.path.normpath(os.path.join(media_folder, filename))

            if os.path.exists(filepath):
                remote_file_size = int(response.headers.get('content-length', 0))
                local_file_size = os.path.getsize(filepath)

                if remote_file_size == local_file_size:
                    self.log(self.tr("File already exists and is complete, skipping: {filepath}", filepath=filepath) if self.tr else f"File already exists and is complete, skipping: {filepath}")
                    with self.lock:
                        self.skipped_files.append(filepath)
                    return
                else:
                    self.log(self.tr("File is incomplete or corrupted, deleting and re-downloading: {filepath}", filepath=filepath) if self.tr else f"File is incomplete or corrupted, deleting and re-downloading: {filepath}")
                    os.remove(filepath)

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            start_time = time.time()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1048576):  # 1MB
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(filepath)
                        self.log(self.tr("Download cancelled from {media_url}", media_url=media_url) if self.tr else f"Download cancelled from {media_url}")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        elapsed_time = time.time() - start_time
                        speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                        remaining_time = (total_size - downloaded_size) / speed if speed > 0 else 0

                        if self.update_progress_callback:
                            self.update_progress_callback(downloaded_size, total_size, file_id=media_url, file_path=filepath, speed=speed, eta=remaining_time)

            if not self.cancel_requested.is_set():
                with self.lock:
                    self.completed_files += 1
                    self.log(self.tr("Download success from {media_url}", media_url=media_url) if self.tr else f"Download success from {media_url}")
                    if self.update_global_progress_callback:
                        self.update_global_progress_callback(self.completed_files, self.total_files)

        except Exception as e:
            self.log(self.tr("Error downloading: {e}", e=e) if self.tr else f"Error downloading: {e}")
            with self.lock:
                retries = self.failed_retry_count.get(media_url, 0)
                if retries < 1:
                    self.failed_retry_count[media_url] = retries + 1
                    self.failed_files.append(media_url)
                    self.log(self.tr("Retrying download for {media_url}", media_url=media_url) if self.tr else f"Retrying download for {media_url}")
                else:
                    if 'filepath' in locals() and os.path.exists(filepath):
                        os.remove(filepath)
                    self.log(self.tr("Already retried once, not retrying again for {media_url}", media_url=media_url) if self.tr else f"Already retried once, not retrying again for {media_url}")

    def increment_failed_files(self, media_url: str):
        """
        Incrementa el contador de archivos fallidos y maneja los reintentos.
        """
        with self.lock:
            retries = self.failed_retry_count.get(media_url, 0)
            if retries < 1:
                self.failed_retry_count[media_url] = retries + 1
                self.failed_files.append(media_url)
                self.log(self.tr("Retrying download for {media_url}", media_url=media_url) if self.tr else f"Retrying download for {media_url}")
            else:
                self.log(self.tr("Already retried once, not retrying again for {media_url}", media_url=media_url) if self.tr else f"Already retried once, not retrying again for {media_url}")

    def get_remote_file_size(self, media_url: str, filename: str) -> Tuple[str, str, Optional[int]]:
        """
        Obtiene el tamaño del archivo remoto mediante una solicitud HEAD.
        """
        api_url = media_url
        self.log(self.tr(f"Fetching remote file size for {filename} from {api_url}", api_url=api_url, filename=filename) if self.tr else f"Fetching remote file size for {filename} from {api_url}")

        try:
            with self.rate_limit:
                response = self.session.head(api_url, headers=self.headers, allow_redirects=True, timeout=10)
            response.raise_for_status()
            size = int(response.headers.get('Content-Length', 0))
            return media_url, filename, size
        except requests.exceptions.RequestException as e:
            self.log(self.tr(f"Error getting size for {filename}: {e}", e=e) if self.tr else f"Error getting size for {filename}: {e}")
            return media_url, filename, None

    def download_media(
        self, 
        site: str, 
        user_id: str, 
        service: str, 
        query: Optional[str] = None, 
        download_all: bool = False, 
        initial_offset: int = 0
    ):
        """
        Inicia el proceso de descarga de medios basado en las publicaciones del usuario.
        """
        try:
            self.log(self.tr("Starting download process...") if self.tr else "Starting download process...")

            # Código principal de descarga
            posts = self.fetch_user_posts(site, user_id, service, query=query, initial_offset=initial_offset, log_fetching=download_all)
            if not posts:
                self.log(self.tr("No posts found for this user.") if self.tr else "No posts found for this user.")
                return

            if not download_all:
                posts = posts[:50]  # Limitar a los primeros 50 posts

            grouped_media_urls = defaultdict(list)

            # Construir la ruta específica de la carpeta para el user_id
            specific_folder = os.path.join(self.download_folder, user_id)
            os.makedirs(specific_folder, exist_ok=True)

            if not os.listdir(specific_folder):
                self.log(self.tr("No existing files found in the specific folder, skipping duplicate check.") if self.tr else "No existing files found in the specific folder, skipping duplicate check.")
                for post in posts:
                    media_urls = self.process_post(post)
                    for media_url in media_urls:
                        extension = os.path.splitext(media_url)[1].lower()
                        if (extension in self.image_extensions and not self.download_images) or \
                        (extension in self.video_extensions and not self.download_videos) or \
                        (extension in self.compressed_extensions and not self.download_compressed):
                            continue  # Skip non-selected file types
                        grouped_media_urls[post['id']].append(media_url)
            else:
                self.log(self.tr("Verifying existing files for duplicates in the specific folder...") if self.tr else "Verifying existing files for duplicates in the specific folder...")
                existing_files = {}
                for root, _, files in os.walk(specific_folder):
                    for file in files:
                        filepath = os.path.join(root, file)
                        existing_files[file] = os.path.getsize(filepath)

                # Recolectar todas las URLs de medios y nombres de archivos
                all_media_urls: List[Tuple[str, str]] = []
                for post in posts:
                    media_urls = self.process_post(post)
                    for media_url in media_urls:
                        extension = os.path.splitext(media_url)[1].lower()
                        if (extension in self.image_extensions and not self.download_images) or \
                        (extension in self.video_extensions and not self.download_videos) or \
                        (extension in self.compressed_extensions and not self.download_compressed):
                            continue  # Skip non-selected file types
                        filename = os.path.basename(urlparse(media_url).path).split('?')[0]
                        all_media_urls.append((media_url, filename))

                # Obtener tamaños de archivos remotos en paralelo
                size_futures = [self.executor.submit(self.get_remote_file_size, media_url, filename) for media_url, filename in all_media_urls]
                remote_sizes: Dict[str, Optional[int]] = {}
                for future in as_completed(size_futures):
                    media_url, filename, size = future.result()
                    remote_sizes[filename] = size

                # Filtrar archivos existentes y tamaños
                for media_url, filename in all_media_urls:
                    if filename in existing_files:
                        local_size = existing_files[filename]
                        remote_size = remote_sizes.get(filename)

                        if remote_size is not None and local_size >= remote_size:
                            self.log(self.tr("File already exists with the same or larger size, skipping: {filename}", filename=filename) if self.tr else f"File already exists with the same or larger size, skipping: {filename}")
                            with self.lock:
                                self.skipped_files.append(filename)
                            continue

                    grouped_media_urls[post['id']].append(media_url)

            self.total_files = sum(len(urls) for urls in grouped_media_urls.values())
            self.completed_files = 0

            if self.download_mode == 'queue':
                for post_id, media_urls in grouped_media_urls.items():
                    for media_url in media_urls:
                        self.process_media_element(media_url, user_id, post_id)
            else:
                for post_id, media_urls in grouped_media_urls.items():
                    for media_url in media_urls:
                        future = self.executor.submit(self.process_media_element, media_url, user_id, post_id)
                        with self.lock:
                            self.futures.append(future)

                # Esperar a que todas las descargas concurrentes finalicen
                for future in as_completed(self.futures):
                    if self.cancel_requested.is_set():
                        break

            # Manejo de archivos fallidos
            with self.lock:
                if self.failed_files:
                    self.log(self.tr("Retrying failed downloads...") if self.tr else "Retrying failed downloads...")
                    failed_urls = self.failed_files.copy()
                    self.failed_files.clear()

            for media_url in failed_urls:
                if self.cancel_requested.is_set():
                    break
                self.process_media_element(media_url, user_id)

        except Exception as e:
            self.log(self.tr(f"Unexpected error during download: {e}", e=e) if self.tr else f"Unexpected error during download: {e}")
        finally:
            self.shutdown_executor()


        def download_single_post(self, site: str, post_id: str, service: str, user_id: str):
            """
            Descarga los medios de una publicación específica.
            """
            try:
                post = self.fetch_single_post(site, post_id, service, user_id)
                if not post:
                    self.log(self.tr("No post found for this ID.") if self.tr else "No post found for this ID.")
                    return

                media_urls = self.process_post(post)
                grouped_media_urls = defaultdict(list)
                for media_url in media_urls:
                    grouped_media_urls[post['id']].append(media_url)

                self.total_files = len(media_urls)
                self.completed_files = 0

                if self.download_mode == 'queue':
                    for media_url in media_urls:
                        self.process_media_element(media_url, user_id, post['id'])
                else:
                    futures = [self.executor.submit(self.process_media_element, media_url, user_id, post['id']) for media_url in media_urls]
                    with self.lock:
                        self.futures.extend(futures)

                    for future in as_completed(futures):
                        if self.cancel_requested.is_set():
                            break

                # Manejo de archivos fallidos
                with self.lock:
                    if self.failed_files:
                        self.log(self.tr("Retrying failed downloads...") if self.tr else "Retrying failed downloads...")
                        failed_urls = self.failed_files.copy()
                        self.failed_files.clear()

                for media_url in failed_urls:
                    if self.cancel_requested.is_set():
                        break
                    self.process_media_element(media_url, user_id)

            except Exception as e:
                self.log(self.tr(f"Error during download: {e}", e=e) if self.tr else f"Error during download: {e}")
            finally:
                self.shutdown_executor()

    def fetch_single_post(self, site: str, post_id: str, service: str, user_id: str) -> Optional[Dict]:
        """
        Obtiene una publicación específica de la API.
        """
        api_url = f"https://{site}.su/api/v1/{service}/post/{post_id}"
        self.log(self.tr(f"Fetching post from {api_url}", api_url=api_url) if self.tr else f"Fetching post from {api_url}")

        try:
            response = self.safe_request(api_url)
            if response:
                return response.json()
            else:
                self.log(self.tr("Failed to fetch post from {api_url}", api_url=api_url) if self.tr else f"Failed to fetch post from {api_url}")
        except ValueError as e:
            self.log(self.tr("Error parsing JSON response: {e}", e=e) if self.tr else f"Error parsing JSON response: {e}")
        except Exception as e:
            self.log(self.tr(f"Error fetching post: {e}", e=e) if self.tr else f"Error fetching post: {e}")
        return None

