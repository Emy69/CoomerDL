from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from urllib.parse import quote_plus, urlencode, urljoin, urlparse
import os
import re
import requests
import threading
import time

class Downloader:
    def __init__(self, download_folder, max_workers=5, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, headers=None,
                 download_images=True, download_videos=True, download_compressed=True, tr=None, folder_structure='default',rate_limit_interval=2.0):

        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.cancel_requested = threading.Event()  # Event to handle cancellation requests
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
        self.domain_last_request = defaultdict(float)  # Rastrea la última solicitud por dominio
        self.rate_limit_interval = rate_limit_interval
        self.download_mode = "multi"  # Download mode: 'multi' for concurrent, 'queue' for sequential
        self.video_extensions = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv', '.m4v')
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        self.document_extensions = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')
        self.compressed_extensions = ('.zip', '.rar', '.7z', '.tar', '.gz')
        self.download_images = download_images
        self.download_videos = download_videos
        self.download_compressed = download_compressed
        self.futures = []  # List to keep track of future objects for concurrent tasks
        self.total_files = 0
        self.completed_files = 0
        self.skipped_files = []  
        self.failed_files = []
        self.start_time = None
        self.tr = tr
        self.shutdown_called = False  # Flag to prevent multiple shutdowns of the executor
        self.folder_structure = folder_structure

    def log(self, message):
        if self.log_callback:
            self.log_callback(self.tr(message) if self.tr else message)

    def set_download_mode(self, mode, max_workers):
        self.download_mode = mode
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.rate_limit = Semaphore(max_workers)

    def request_cancel(self):
        self.cancel_requested.set()
        self.log(self.tr("Download cancellation requested."))
        for future in self.futures:
            future.cancel()

    def shutdown_executor(self):
        if not self.shutdown_called:
            self.shutdown_called = True  # Prevent multiple shutdowns
            if self.executor:
                self.executor.shutdown(wait=True) 
            if self.enable_widgets_callback:
                self.enable_widgets_callback()
            self.log(self.tr("All downloads completed or cancelled."))

    def safe_request(self, url, max_retries=5):
        retry_wait = 1
        domain = urlparse(url).netloc

        for attempt in range(max_retries):
            if self.cancel_requested.is_set():
                return None

            with self.domain_locks[domain]:
                # Wait if the last request to this domain was too recent
                last_request_time = self.domain_last_request[domain]
                elapsed_time = time.time() - last_request_time
                if elapsed_time < self.rate_limit_interval:
                    time.sleep(self.rate_limit_interval - elapsed_time)

                try:
                    with self.rate_limit:
                        response = self.session.get(url, stream=True, headers=self.headers)
                    response.raise_for_status()
                    self.domain_last_request[domain] = time.time()  # Update the last request time for the domain
                    return response

                except requests.exceptions.RequestException as e:
                    if e.response and e.response.status_code == 429:
                        self.log(f"Retry {attempt + 1}: Error 429 Too Many Requests for url: {url}, waiting {retry_wait} seconds before retrying.")
                        time.sleep(retry_wait)
                        retry_wait *= 2
                    else:
                        self.log(f"Non-retryable error: {e}")
                        break

        return None

    def fetch_user_posts(self, site, user_id, service, query=None, specific_post_id=None, initial_offset=0, log_fetching=True):
        all_posts = []
        offset = initial_offset
        user_id_encoded = quote_plus(user_id)

        while True:
            if self.cancel_requested.is_set():
                return all_posts

            api_url = f"https://{site}/api/v0/{service}/user/{user_id_encoded}"
            url_query = { "o": offset }
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
                offset += 50  # Move to the next set of posts
            except Exception as e:
                self.log(self.tr("Error fetching user posts: {e}", e=e))
                break

        if specific_post_id:
            return [post for post in all_posts if post['id'] == specific_post_id]
        return all_posts

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

    def process_media_element(self, media_url, user_id, post_id=None):
        # Normalize file path
        extension = os.path.splitext(media_url)[1].lower()
        if self.cancel_requested.is_set():
            return

        if (extension in self.image_extensions and not self.download_images) or \
        (extension in self.video_extensions and not self.download_videos) or \
        (extension in self.compressed_extensions and not self.download_compressed):
            self.log(self.tr("Skipping {media_url} due to download settings.", media_url=media_url))
            return

        self.log(self.tr("Starting download from {media_url}", media_url=media_url))

        try:
            response = self.safe_request(media_url)
            if response is None:
                self.log(self.tr("Failed to download after multiple retries: {media_url}", media_url=media_url))
                self.failed_files.append(media_url)
                return

            media_folder = self.get_media_folder(extension, user_id, post_id)
            os.makedirs(media_folder, exist_ok=True)

            filename = os.path.basename(media_url).split('?')[0]
            filename = self.sanitize_filename(filename)
            filepath = os.path.normpath(os.path.join(media_folder, filename))  # Normalize path

            # Improved file existence check
            if os.path.exists(filepath):
                remote_file_size = int(response.headers.get('content-length', 0))
                local_file_size = os.path.getsize(filepath)

                if remote_file_size == local_file_size:
                    self.log(self.tr("File already exists and is complete, skipping: {filepath}", filepath=filepath))
                    self.skipped_files.append(filepath)
                    return
                else:
                    self.log(self.tr("File is incomplete or corrupted, deleting and re-downloading: {filepath}", filepath=filepath))
                    os.remove(filepath)

            # Continue with the downloading process if the file doesn't exist or is incomplete
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            self.start_time = time.time()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1048576):
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(filepath)
                        self.log(self.tr("Download cancelled from {media_url}", media_url=media_url))
                        return
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    elapsed_time = time.time() - self.start_time
                    speed = downloaded_size / elapsed_time
                    remaining_time = (total_size - downloaded_size) / speed if speed > 0 else 0

                    if self.update_progress_callback:
                        self.update_progress_callback(downloaded_size, total_size, file_id=media_url, file_path=filepath, speed=speed, eta=remaining_time)

            if not self.cancel_requested.is_set():
                self.completed_files += 1
                self.log(self.tr("Download success from {media_url}", media_url=media_url))
                if self.update_global_progress_callback:
                    self.update_global_progress_callback(self.completed_files, self.total_files)

        except Exception as e:
            self.log(self.tr("Error downloading: {e}", e=e))
            self.failed_files.append(media_url)
        
    def get_remote_file_size(self, media_url, filename):
        try:
            # Realizar una solicitud HEAD para obtener información del archivo
            response = requests.head(media_url, allow_redirects=True)

            # Comprobar si la solicitud fue exitosa
            if response.status_code == 200:
                # Obtener el tamaño del archivo desde el encabezado 'Content-Length'
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

            posts = self.fetch_user_posts(site, user_id, service, query=query, initial_offset=initial_offset, log_fetching=download_all)
            if not posts:
                self.log(self.tr("No posts found for this user."))
                return

            if not download_all:
                posts = posts[:50]  # Limitar a los primeros 50 posts

            futures = []
            grouped_media_urls = defaultdict(list)

            # Construir la ruta específica de la carpeta para el user_id
            specific_folder = os.path.join(self.download_folder, user_id)

            # Verificar y crear la carpeta específica si no existe
            os.makedirs(specific_folder, exist_ok=True)

            # Verificar si la carpeta de descargas está vacía
            if not os.listdir(specific_folder):
                self.log(self.tr("No existing files found in the specific folder, skipping duplicate check."))
                for post in posts:
                    media_urls = self.process_post(post)
                    for media_url in media_urls:
                        extension = os.path.splitext(media_url)[1].lower()
                        # Filtrar según los tipos de archivo seleccionados
                        if (extension in self.image_extensions and not self.download_images) or \
                        (extension in self.video_extensions and not self.download_videos) or \
                        (extension in self.compressed_extensions and not self.download_compressed):
                            continue  # Saltar archivos no seleccionados

                        grouped_media_urls[post['id']].append(media_url)
            else:
                # Continuar con el flujo actual
                self.log(self.tr("Verifying existing files for duplicates in the specific folder..."))
                existing_files = {}
                for root, _, files in os.walk(specific_folder):
                    for file in files:
                        filepath = os.path.join(root, file)
                        existing_files[file] = os.path.getsize(filepath)

                # Recolectar todas las URLs de medios y nombres de archivos
                all_media_urls = []
                for post in posts:
                    media_urls = self.process_post(post)
                    for media_url in media_urls:
                        extension = os.path.splitext(media_url)[1].lower()
                        # Filtrar según los tipos de archivo seleccionados
                        if (extension in self.image_extensions and not self.download_images) or \
                        (extension in self.video_extensions and not self.download_videos) or \
                        (extension in self.compressed_extensions and not self.download_compressed):
                            continue  # Saltar archivos no seleccionados

                        filename = os.path.basename(media_url).split('?')[0]
                        all_media_urls.append((media_url, filename))

                # Obtener tamaños de archivos remotos en paralelo
                remote_sizes = {filename: None for _, filename in all_media_urls}
                size_futures = []
                for media_url, filename in all_media_urls:
                    size_futures.append(self.executor.submit(self.get_remote_file_size, media_url, filename))

                for future in as_completed(size_futures):
                    media_url, filename, size = future.result()
                    remote_sizes[filename] = size

                # Filtrar archivos existentes y tamaños
                for media_url, filename in all_media_urls:
                    if filename in existing_files:
                        local_size = existing_files[filename]
                        remote_size = remote_sizes[filename]

                        if remote_size is not None and local_size >= remote_size:
                            self.log(self.tr("File already exists with the same or larger size, skipping: {filename}", filename=filename))
                            self.skipped_files.append(filename)
                            continue

                    grouped_media_urls[post['id']].append(media_url)

            self .total_files = sum(len(urls) for urls in grouped_media_urls.values())
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

            # Manejo de archivos fallidos
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