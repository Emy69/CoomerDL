"""
This script defines a Downloader class responsible for handling media downloads from various sources.
The class supports downloading images, videos, and compressed files, and manages the download process using threading and a thread pool.
It includes features for logging, progress tracking, retry mechanisms, and handling cancellations.

Key functionalities:
- Fetching posts from a user profile.
- Processing and downloading media elements.
- Handling multiple download types (images, videos, compressed files).
- Managing download progress and retries.
- Allowing for customizable folder structures for downloads.
"""
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
        """
        Initialize the Downloader class.

        :param download_folder: Directory where the downloaded files will be saved.
        :param max_workers: Maximum number of concurrent download threads.
        :param log_callback: Function for logging messages during the download process.
        :param enable_widgets_callback: Function to re-enable UI widgets after downloads complete.
        :param update_progress_callback: Function to update download progress for each file.
        :param update_global_progress_callback: Function to update overall download progress.
        :param headers: HTTP headers to use during requests.
        :param download_images: Flag to enable/disable downloading images.
        :param download_videos: Flag to enable/disable downloading videos.
        :param download_compressed: Flag to enable/disable downloading compressed files.
        :param tr: Function for translating text messages (for localization).
        :param folder_structure: The folder structure used to organize downloaded files.
        """
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
        """
        Log a message using the provided log callback function.
        If a translation function is provided, the message is translated before logging.
        
        :param message: The message to be logged.
        """
        if self.log_callback:
            self.log_callback(self.tr(message) if self.tr else message)

    def set_download_mode(self, mode, max_workers):
        """
        Set the download mode and adjust the number of concurrent workers.
        
        :param mode: The download mode ('multi' for concurrent, 'queue' for sequential).
        :param max_workers: The maximum number of concurrent workers.
        """
        self.download_mode = mode
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.rate_limit = Semaphore(max_workers)

    def request_cancel(self):
        """
        Request the cancellation of ongoing downloads.
        Sets the cancellation event and attempts to cancel all running futures.
        """
        self.cancel_requested.set()
        self.log(self.tr("Download cancellation requested."))
        for future in self.futures:
            future.cancel()

    def shutdown_executor(self):
        """
        Shutdown the thread pool executor after all tasks are complete or cancelled.
        This method is called once to ensure resources are properly released.
        """
        if not self.shutdown_called:
            self.shutdown_called = True  # Prevent multiple shutdowns
            if self.executor:
                self.executor.shutdown(wait=True) 
            if self.enable_widgets_callback:
                self.enable_widgets_callback()
            self.log(self.tr("All downloads completed or cancelled."))

    def safe_request(self, url, max_retries=5):
        """
        Perform a GET request with retry logic and rate limiting by domain.
        
        :param url: The URL to request.
        :param max_retries: Maximum number of retries in case of failure.
        :return: The response object if successful, None otherwise.
        """
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
        """
        Fetch posts from a user's profile using the specified API.
        
        :param site: The base URL of the site.
        :param user_id: The ID of the user whose posts are to be fetched.
        :param service: The service being used (e.g., 'user', 'posts').
        :param query: Optional query to filter posts.
        :param specific_post_id: Fetch only a specific post by its ID.
        :param initial_offset: The starting offset for pagination.
        :param log_fetching: Whether to log the fetching process.
        :return: A list of posts retrieved from the user's profile.
        """
        all_posts = []
        offset = initial_offset
        user_id_encoded = quote_plus(user_id)

        while True:
            if self.cancel_requested.is_set():
                return all_posts

            api_url = f"https://{site}/api/v1/{service}/user/{user_id_encoded}"
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
        """
        Extract media URLs from a post's data.
        
        :param post: The post data containing media files.
        :return: A list of media URLs extracted from the post.
        """
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
        """
        Sanitize a filename by replacing illegal characters with underscores.
        
        :param filename: The original filename.
        :return: A sanitized filename safe for use in file systems.
        """
        return re.sub(r'[<>:"/\\|?*]', '_', filename)

    def get_media_folder(self, extension, user_id, post_id=None):
        """
        Determine the folder path for storing a media file based on its extension and user ID.
        
        :param extension: The file extension of the media.
        :param user_id: The ID of the user who posted the media.
        :param post_id: The ID of the post containing the media (optional).
        :return: The path to the folder where the media should be stored.
        """
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

    def download_media(self, site, user_id, service, query=None, download_all=False, initial_offset=0):
        """
        Download media from a user's posts on the specified site.
        
        :param site: The base URL of the site.
        :param user_id: The ID of the user whose media is to be downloaded.
        :param service: The service being used (e.g., 'user', 'posts').
        :param query: Optional query to filter posts.
        :param download_all: Whether to download all posts or just the first 50.
        :param initial_offset: The starting offset for pagination.
        """
        try:
            posts = self.fetch_user_posts(site, user_id, service, query=query, initial_offset=initial_offset, log_fetching=download_all)
            if not posts:
                self.log(self.tr("No posts found for this user."))
                return

            if not download_all:
                posts = posts[:50]  # Limit to the first 50 posts

            futures = []
            grouped_media_urls = defaultdict(list)

            for post in posts:
                media_urls = self.process_post(post)
                for media_url in media_urls:
                    grouped_media_urls[post['id']].append(media_url)

            self.total_files = sum(len(urls) for urls in grouped_media_urls.values())
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

    def download_single_post(self, site, post_id, service, user_id):
        """
        Download media from a specific post by its ID.
        
        :param site: The base URL of the site.
        :param post_id: The ID of the post to download.
        :param service: The service being used (e.g., 'user', 'posts').
        :param user_id: The ID of the user who posted the media.
        """
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
        """
        Fetch the details of a single post by its ID.
        
        :param site: The base URL of the site.
        :param post_id: The ID of the post to fetch.
        :param service: The service being used (e.g., 'user', 'posts').
        :return: The post data as a dictionary, or None if an error occurs.
        """
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