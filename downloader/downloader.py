import re
import threading
import requests
import os
from urllib.parse import urljoin, quote_plus, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from threading import Semaphore
from collections import defaultdict

class Downloader:
    def __init__(self, download_folder, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, headers=None,
                 download_images=True, download_videos=True, download_compressed=True, tr=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.cancel_requested = threading.Event()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'Accept': 'application/json',
        }
        self.media_counter = 0
        self.session = requests.Session()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.rate_limit = Semaphore(10)
        self.download_mode = "multi"
        self.max_workers = 10
        self.video_extensions = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv', '.m4v')
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        self.document_extensions = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')
        self.compressed_extensions = ('.zip', '.rar', '.7z', '.tar', '.gz')
        self.download_images = download_images
        self.download_videos = download_videos
        self.download_compressed = download_compressed
        self.futures = []
        self.total_files = 0
        self.completed_files = 0
        self.tr = tr
        self.shutdown_called = False  

    def log(self, message):
        if self.log_callback:
            self.log_callback(self.tr(message) if self.tr else message)

    def set_download_mode(self, mode, max_workers):
        self.download_mode = mode
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

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

    def safe_request(self, url, max_retries=5):
        retry_wait = 1
        for attempt in range(max_retries):
            if self.cancel_requested.is_set():
                return None
            try:
                with self.rate_limit:
                    response = self.session.get(url, stream=True, headers=self.headers)
                response.raise_for_status()
                return response
            except (requests.ConnectionError, requests.HTTPError, requests.TooManyRedirects) as e:
                self.log(self.tr(f"Retry {attempt + 1}: Error {e}, waiting {retry_wait} seconds before retrying."))
                time.sleep(retry_wait)
                retry_wait *= 2
            except requests.exceptions.RequestException as e:
                if e.response and e.response.status_code == 429:
                    self.log(self.tr(f"Retry {attempt + 1}: Error 429 Too Many Requests for url: {url}, waiting {retry_wait} seconds before retrying."))
                    time.sleep(retry_wait)
                    retry_wait *= 2
                else:
                    self.log(self.tr(f"Non-retryable error: {e}"))
                    break
        return None

    def fetch_user_posts(self, site, user_id, service, specific_post_id=None):
        all_posts = []
        offset = 0
        user_id_encoded = quote_plus(user_id)

        while True:
            if self.cancel_requested.is_set():
                return all_posts
            api_url = f"https://{site}.su/api/v1/{service}/user/{user_id_encoded}?o={offset}"
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

    def get_media_folder(self, extension, user_id):
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

        media_folder = os.path.join(self.download_folder, user_id, folder_name)
        return media_folder

    def process_media_element(self, media_url, user_id):
        if self.cancel_requested.is_set():
            return

        extension = os.path.splitext(media_url)[1].lower()

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
                return

            media_folder = self.get_media_folder(extension, user_id)
            os.makedirs(media_folder, exist_ok=True)

            filename = os.path.basename(media_url).split('?')[0]
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = os.path.join(media_folder, filename)

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1048576):
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(filepath)
                        self.log(self.tr("Download cancelled from {media_url}", media_url=media_url))
                        return
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if self.update_progress_callback:
                        self.update_progress_callback(downloaded_size, total_size, file_id=media_url, file_path=filepath)  # Actualiza la barra de progreso

            if not self.cancel_requested.is_set():
                self.completed_files += 1
                self.log(self.tr("Download success from {media_url}", media_url=media_url))
                if self.update_global_progress_callback:
                    self.update_global_progress_callback(self.completed_files, self.total_files)

        except Exception as e:
            self.log(self.tr("Error downloading: {e}", e=e))


    def download_media(self, site, user_id, service, download_all):
        try:
            posts = self.fetch_user_posts(site, user_id, service)
            if not posts:
                self.log(self.tr("No posts found for this user."))
                return
            
            if not download_all:
                posts = posts[:50]

            futures = []
            grouped_media_urls = defaultdict(list)

            # Agrupar URLs por subdominio
            for post in posts:
                media_urls = self.process_post(post)
                for media_url in media_urls:
                    subdomain = urlparse(media_url).netloc
                    grouped_media_urls[subdomain].append(media_url)

            self.total_files = sum(len(urls) for urls in grouped_media_urls.values())
            self.completed_files = 0

            for subdomain, media_urls in grouped_media_urls.items():
                for media_url in media_urls:
                    if self.download_mode == 'queue':
                        self.process_media_element(media_url, user_id)
                    else:
                        future = self.executor.submit(self.process_media_element, media_url, user_id)
                        futures.append(future)

            if self.download_mode == 'multi':
                for future in as_completed(futures):
                    if self.cancel_requested.is_set():
                        break

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

            # Agrupar URLs por subdominio
            for media_url in media_urls:
                subdomain = urlparse(media_url).netloc
                grouped_media_urls[subdomain].append(media_url)

            self.total_files = len(media_urls)
            self.completed_files = 0

            for subdomain, media_urls in grouped_media_urls.items():
                for media_url in media_urls:
                    if self.download_mode == 'queue':
                        self.process_media_element(media_url, user_id)
                    else:
                        future = self.executor.submit(self.process_media_element, media_url, user_id)
                        futures.append(future)

            if self.download_mode == 'multi':
                for future in as_completed(futures):
                    if self.cancel_requested.is_set():
                        break

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