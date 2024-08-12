"""
This script defines a BunkrDownloader class, designed to handle the downloading of media files from Bunkr posts and profiles.
It supports downloading images and videos concurrently using threading, provides logging and progress updates, and handles cancellations and retries.

Key functionalities:
- Downloading media files from Bunkr posts and profiles.
- Concurrent downloading using a thread pool.
- Logging and progress updates throughout the download process.
- Handling download cancellations and retry logic.
"""

import os
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
import uuid
import re

class BunkrDownloader:
    def __init__(self, download_folder, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, headers=None, max_workers=5):
        """
        Initialize the BunkrDownloader class.

        :param download_folder: Directory where the downloaded files will be saved.
        :param log_callback: Function for logging messages during the download process.
        :param enable_widgets_callback: Function to re-enable UI widgets after downloads complete.
        :param update_progress_callback: Function to update download progress for each file.
        :param update_global_progress_callback: Function to update overall download progress.
        :param headers: HTTP headers to use during requests.
        :param max_workers: Maximum number of concurrent download threads.
        """
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.cancel_requested = False  # Flag to indicate if a cancellation request has been made
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # Thread pool executor for concurrent downloads
        self.total_files = 0
        self.completed_files = 0

    def log(self, message, url=None):
        """
        Log a message using the provided log callback function. If a URL is provided, the domain is included in the log.

        :param message: The message to be logged.
        :param url: Optional URL associated with the log message.
        """
        domain = urlparse(url).netloc if url else "General"
        full_message = f"{domain}: {message}"
        if self.log_callback:
            self.log_callback(full_message)

    def request_cancel(self):
        """
        Request the cancellation of ongoing downloads. Sets the cancellation flag and shuts down the executor.
        """
        self.cancel_requested = True
        self.log("Download has been cancelled.")
        self.shutdown_executor()

    def shutdown_executor(self):
        """
        Shutdown the thread pool executor immediately, stopping any ongoing tasks.
        """
        self.executor.shutdown(wait=False)
        self.log("Executor shut down.")

    def clean_filename(self, filename):
        """
        Sanitize a filename by replacing illegal characters with underscores.

        :param filename: The original filename.
        :return: A sanitized filename safe for use in file systems.
        """
        return re.sub(r'[<>:"/\\|?*\u200b]', '_', filename)

    def download_file(self, url_media, ruta_carpeta, file_id):
        """
        Download a file from the specified URL and save it to the given folder.

        :param url_media: The URL of the media file to download.
        :param ruta_carpeta: The path to the folder where the file will be saved.
        :param file_id: An identifier for the file being downloaded (used for progress updates).
        """
        if self.cancel_requested:
            self.log("Download cancelled by the user.", url=url_media)
            return

        max_attempts = 3
        delay = 1
        for attempt in range(max_attempts):
            try:
                self.log(f"Attempting to download {url_media} (Attempt {attempt + 1}/{max_attempts})")
                response = self.session.get(url_media, headers=self.headers, stream=True)
                response.raise_for_status()
                file_name = os.path.basename(urlparse(url_media).path)
                file_path = os.path.join(ruta_carpeta, file_name)
                
                if os.path.exists(file_path):
                    self.log(f"File already exists, skipping: {file_path}")
                    return
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                # Download the file in chunks
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                        if self.cancel_requested:
                            self.log("Download cancelled during the file download.", url=url_media)
                            file.close()
                            os.remove(file_path)
                            return
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        if self.update_progress_callback:
                            self.update_progress_callback(downloaded_size, total_size, file_id=file_id, file_path=file_path)

                self.log(f"File downloaded: {file_name}", url=url_media)
                self.completed_files += 1
                if self.update_global_progress_callback:
                    self.update_global_progress_callback(self.completed_files, self.total_files)
                break
            except requests.RequestException as e:
                if response.status_code == 429:
                    self.log(f"Rate limit exceeded. Retrying after {delay} seconds.")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff for rate limiting
                else:
                    self.log(f"Failed to download from {url_media}: {e}. Attempt {attempt + 1} of {max_attempts}", url=url_media)
                    if attempt < max_attempts - 1:
                        time.sleep(3)

    def descargar_post_bunkr(self, url_post):
        """
        Download media from a specific Bunkr post.

        :param url_post: The URL of the Bunkr post to download from.
        """
        try:
            self.log(f"Starting download for post: {url_post}")
            response = self.session.get(url_post, headers=self.headers)
            self.log(f"Response status code: {response.status_code} for {url_post}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract and sanitize the file name for the post
                file_name_tag = soup.find('h1', {'class': 'text-[24px] font-bold text-dark dark:text-white'})
                if file_name_tag:
                    file_name = file_name_tag.text.strip()
                else:
                    file_name = f"bunkr_post_{uuid.uuid4()}"
                file_name = self.clean_filename(file_name)
                ruta_carpeta = os.path.join(self.download_folder, file_name)
                os.makedirs(ruta_carpeta, exist_ok=True)

                # Find media URLs in the post
                media_urls = []
                image_tag = soup.select_one("div.lightgallery img")
                video_tag = soup.select_one("video source")
                if image_tag and 'src' in image_tag.attrs:
                    img_url = image_tag['src']
                    self.log(f"Found image URL: {img_url}")
                    media_urls.append((img_url, ruta_carpeta))
                if video_tag and 'src' in video_tag.attrs:
                    video_url = video_tag['src']
                    self.log(f"Found video URL: {video_url}")
                    media_urls.append((video_url, ruta_carpeta))

                self.total_files = len(media_urls)
                futures = [self.executor.submit(self.download_file, url, folder, str(uuid.uuid4())) for url, folder in media_urls]
                for future in as_completed(futures):
                    if self.cancel_requested:
                        self.log("Cancelling remaining downloads.")
                        break
                    future.result()

                self.log("Download initiated for all media.")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()
            else:
                self.log(f"Failed to access the post {url_post}: Status {response.status_code}")
        except Exception as e:
            self.log(f"Failed to access the post {url_post}: {e}")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()

    def descargar_perfil_bunkr(self, url_perfil):
        """
        Download media from a specific Bunkr profile.

        :param url_perfil: The URL of the Bunkr profile to download from.
        """
        try:
            self.log(f"Starting download for profile: {url_perfil}")
            response = self.session.get(url_perfil, headers=self.headers)
            self.log(f"Response status code: {response.status_code} for {url_perfil}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract and sanitize the folder name for the profile
                file_name_tag = soup.find('h1', {'class': 'text-[24px] font-bold text-dark dark:text-white'})
                if file_name_tag:
                    folder_name = file_name_tag.text.strip()
                else:
                    folder_name = f"bunkr_profile_{uuid.uuid4()}"
                folder_name = self.clean_filename(folder_name)
                ruta_carpeta = os.path.join(self.download_folder, folder_name)
                os.makedirs(ruta_carpeta, exist_ok=True)
                
                # Find media URLs in the profile
                media_urls = []
                links = soup.select("div.grid-images_box a.grid-images_box-link")
                total_links = len(links)

                for idx, link in enumerate(links):
                    if self.cancel_requested:
                        self.log("Cancelling remaining downloads.")
                        break

                    # Update progress for processing the profile
                    self.update_progress_callback(idx, total_links, file_id=None, file_path=None)

                    image_page_url = link['href']
                    self.log(f"Processing image page URL: {image_page_url}")
                    image_response = self.session.get(image_page_url, headers=self.headers)
                    self.log(f"Image page response status code: {image_response.status_code} for {image_page_url}")
                    if image_response.status_code == 200:
                        image_soup = BeautifulSoup(image_response.text, 'html.parser')
                        image_tag = image_soup.select_one("div.lightgallery img")
                        video_tag = image_soup.select_one("video source")
                        if image_tag and 'src' in image_tag.attrs:
                            img_url = image_tag['src']
                            self.log(f"Found image URL: {img_url}")
                            media_urls.append((img_url, ruta_carpeta))
                        if video_tag and 'src' in video_tag.attrs:
                            video_url = video_tag['src']
                            self.log(f"Found video URL: {video_url}")
                            media_urls.append((video_url, ruta_carpeta))

                self.total_files = len(media_urls)
                futures = [self.executor.submit(self.download_file, url, folder, str(uuid.uuid4())) for url, folder in media_urls]
                for future in as_completed(futures):
                    if self.cancel_requested:
                        self.log("Cancelling remaining downloads.")
                        break
                    future.result()

                self.log("Download initiated for all media.")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()
            else:
                self.log(f"Failed to access the profile {url_perfil}: Status {response.status_code}")
        except Exception as e:
            self.log(f"Failed to access the profile {url_perfil}: {e}")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()
