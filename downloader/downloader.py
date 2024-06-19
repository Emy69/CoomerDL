import re
import threading
import requests
import os
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from threading import Semaphore
from tkinter import messagebox

class Downloader:
    def __init__(self, download_folder, log_callback=None, download_images=True, 
                 download_videos=True, enable_widgets_callback=None, update_speed_callback=None, headers=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_speed_callback = update_speed_callback
        self.cancel_requested = threading.Event()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'Accept': 'application/json',
        }
        self.media_counter = 0
        self.download_images = download_images
        self.download_videos = download_videos
        self.session = requests.Session()
        self.executor = ThreadPoolExecutor(max_workers=10)  # Incrementa el número de trabajadores
        self.rate_limit = Semaphore(10)  # Permite más solicitudes concurrentes
        self.video_extensions = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv')
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def request_cancel(self):
        self.cancel_requested.set()
        self.log("Download cancelled.")
        self.shutdown_executor()

    def shutdown_executor(self):
        self.executor.shutdown(wait=False)
        if self.enable_widgets_callback:
            self.enable_widgets_callback()

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
                self.log(f"Retry {attempt + 1}: Error {e}, waiting {retry_wait} seconds before retrying.")
                time.sleep(retry_wait)
                retry_wait *= 2
            except requests.exceptions.RequestException as e:
                self.log(f"Non-retryable error: {e}")
                break
        return None

    def fetch_user_posts(self, site, user_id, service, specific_post_id=None):
        all_posts = []
        offset = 0

        while True:
            if self.cancel_requested.is_set():
                return all_posts
            api_url = f"https://{site}.su/api/v1/{service}/user/{user_id}?o={offset}"
            self.log(f"Fetching user posts from {api_url}")
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
                self.log(f"Error fetching user posts: {e}")
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

    def process_media_element(self, media_url, user_id):
        if self.cancel_requested.is_set():
            return

        extension = os.path.splitext(media_url)[1].lower()
        if extension in self.video_extensions:
            if not self.download_videos:
                self.log(f"Skipping video: {media_url}")
                return
            media_type = "video"
        elif extension in self.image_extensions:
            if not self.download_images:
                self.log(f"Skipping image: {media_url}")
                return
            media_type = "image"
        else:
            self.log(f"Unsupported media type: {extension}. Skipping {media_url}")
            return

        self.log(f"Starting download: {media_type} from {media_url}")

        try:
            response = self.safe_request(media_url)
            if response is None:
                self.log(f"Failed to download after multiple retries: {media_url}")
                return

            media_folder = os.path.join(self.download_folder, user_id, "videos" if media_type == "video" else "images")
            os.makedirs(media_folder, exist_ok=True)

            filename = os.path.basename(media_url).split('?')[0]
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = os.path.join(media_folder, filename)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1048576):  # 1 MB chunks
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(filepath)
                        self.log(f"Download cancelled for: {media_type} from {media_url}")
                        return
                    f.write(chunk)

            if not self.cancel_requested.is_set():
                self.log(f"Download success: {media_type} from {media_url}")

        except Exception as e:
            self.log(f"Error downloading: {e}")

    def download_media(self, site, user_id, service, download_all):
        posts = self.fetch_user_posts(site, user_id, service)
        if not posts:
            self.log("No posts found for this user.")
            self.shutdown_executor()
            return
        
        if not download_all:
            posts = posts[:50]  # Limita a la primera página (primeros 50 posts)

        futures = []

        try:
            for post in posts:
                media_urls = self.process_post(post)
                for media_url in media_urls:
                    future = self.executor.submit(self.process_media_element, media_url, user_id)
                    futures.append(future)

            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    break

        except Exception as e:
            self.log(f"Error during download: {e}")
        finally:
            self.shutdown_executor()
            self.log("All downloads completed or cancelled.")

    def download_single_post(self, site, post_id, service, user_id, download_images=True, download_videos=True):
        self.download_images = download_images
        self.download_videos = download_videos

        post = self.fetch_user_posts(site, user_id, service, specific_post_id=post_id)
        if not post:
            self.log("No post found for this ID.")
            self.shutdown_executor()
            return
        
        media_urls = self.process_post(post[0])
        futures = []

        try:
            for media_url in media_urls:
                future = self.executor.submit(self.process_media_element, media_url, user_id)
                futures.append(future)

            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    break

        except Exception as e:
            self.log(f"Error during download: {e}")
        finally:
            self.shutdown_executor()
            self.log("All downloads completed or cancelled.")
    
    def fetch_single_post(self, site, post_id, service):
        api_url = f"https://{site}.su/api/v1/{service}/post/{post_id}"
        self.log(f"Fetching post from {api_url}")
        try:
            with self.rate_limit:
                response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(f"Error fetching post: {e}")
            return None