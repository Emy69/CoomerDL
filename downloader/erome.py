import re
import uuid
import requests
import os
import time
import datetime

from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from requests.exceptions import ChunkedEncodingError
from tkinter import messagebox, simpledialog

class EromeDownloader:
    def __init__(self, root, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, download_images=True, download_videos=True, headers=None, language="en", is_profile_download=False, direct_download=False, tr=None, max_workers=5):
        self.root = root
        self.session = requests.Session()
        self.headers = {k: str(v).encode('ascii', 'ignore').decode('ascii') for k, v in (headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }).items()}
        self.log_messages = []  # Store log messages
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.download_images = download_images
        self.download_videos = download_videos
        self.cancel_requested = False
        self.language = language
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # Thread pool for concurrent downloads
        self.total_files = 0
        self.completed_files = 0
        self.is_profile_download = is_profile_download
        self.direct_download = direct_download  # Option for direct downloads without folder creation
        self.tr = tr if tr else lambda x, **kwargs: x.format(**kwargs)  # Translation function

    def request_cancel(self):
        self.cancel_requested = True
        self.log(self.tr("Download cancelled"))
        if self.is_profile_download:
            self.enable_widgets_callback()

    def log(self, message):
        if self.log_callback is not None:
            self.log_callback(message)
        self.log_messages.append(message)

    def shutdown_executor(self):
        self.executor.shutdown(wait=False)
        self.log(self.tr("Executor shut down."))
        if self.is_profile_download:
            self.enable_widgets_callback()

    @staticmethod
    def clean_filename(filename):
        return re.sub(r'[<>:"/\\|?*]', '_', filename.split('?')[0])

    def create_folder(self, folder_name):
        try:
            os.makedirs(folder_name, exist_ok=True)
        except OSError as e:
            self.log(self.tr("Error creating folder: {error}", error=e))
            response = messagebox.askyesno(self.tr("Error"), self.tr("Couldn't create folder: {folder_name}\nWould you like to choose a new name?", folder_name=folder_name), parent=self.root)
            if response:
                new_folder_name = simpledialog.askstring(self.tr("New folder name"), self.tr("Enter new folder name:"), parent=self.root)
                if new_folder_name:
                    folder_name = os.path.join(os.path.dirname(folder_name), self.clean_filename(new_folder_name))
                    try:
                        os.makedirs(folder_name, exist_ok=True)
                    except OSError as e:
                        messagebox.showerror(self.tr("Error"), self.tr("Could not create folder: {folder_name}\nError: {error}", folder_name=folder_name, error=e), parent=self.root)
        return folder_name

    def download_file(self, url, file_path, resource_type, file_id=None, max_retries=999999):
        if self.cancel_requested:
            return

        # Evita sobreescrituras y descargas duplicadas
        if os.path.exists(file_path):
            self.log(self.tr("File already exists, skipping: {file_path}",
                             file_path=file_path))
            return

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.log(self.tr("Start downloading {resource_type}: {file_path}",
                         resource_type=resource_type, file_path=file_path))

        retries = 0
        while retries <= max_retries:
            try:
                with requests.get(url, headers=self.headers,
                                  stream=True, timeout=15) as response:
                    if response.status_code != 200:
                        self.log(self.tr("Error downloading {resource_type}, "
                                         "status code: {status_code}",
                                         resource_type=resource_type,
                                         status_code=response.status_code))
                        break

                    total_size = int(response.headers.get("content-length", 0))
                    downloaded_size = 0
                    start_time = last_update = time.time()

                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=65536):
                            if self.cancel_requested:
                                return
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # Envía actualización cada 0.5 s máx.
                            now = time.time()
                            if now - last_update >= 0.5:
                                elapsed = now - start_time
                                speed = downloaded_size / elapsed if elapsed else 0
                                eta   = ((total_size - downloaded_size) / speed
                                         if speed else None)
                                self.update_progress_callback(
                                    downloaded_size, total_size,
                                    file_id=file_id,
                                    file_path=file_path,
                                    speed=speed,
                                    eta=eta
                                )
                                last_update = now

                    # ─────── Fin de la descarga ───────
                    elapsed = time.time() - start_time
                    final_speed = total_size / elapsed if elapsed else 0

                    # 1· Fuerza la barra al 100 % (sin status)
                    self.update_progress_callback(
                        total_size, total_size,
                        file_id=file_id,
                        file_path=file_path,
                        speed=final_speed,
                        eta=0
                    )

                    # 2· Notifica “Completed” (no altera la barra)
                    self.update_progress_callback(
                        total_size, total_size,
                        file_id=file_id,
                        file_path=file_path,
                        status="Completed"
                    )

                # Contabiliza y avanza la barra global
                self.completed_files += 1
                if self.update_global_progress_callback:
                    self.update_global_progress_callback(
                        self.completed_files, self.total_files
                    )

                self.log(self.tr("Download successful: {resource_type}, "
                                 "{file_path}",
                                 resource_type=resource_type,
                                 file_path=file_path))
                break  # Éxito ⇒ sal del bucle

            except (requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                retries += 1
                self.log(self.tr("Error downloading {resource_type}, "
                                 "attempt {retries}/{max_retries}: {error}",
                                 resource_type=resource_type,
                                 retries=retries,
                                 max_retries=max_retries,
                                 error=e))
                if retries == max_retries:
                    self.log(self.tr("Max retries reached. Failed to "
                                     "download {resource_type}: {file_path}",
                                     resource_type=resource_type,
                                     file_path=file_path))


    def process_album_page(self, page_url, base_folder, download_images=True, download_videos=True):
        try:
            if self.cancel_requested:
                return
            self.log(self.tr("Processing album URL: {page_url}", page_url=page_url))
            response = requests.get(page_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                if not self.direct_download:
                    folder_name = self.clean_filename(soup.find('h1').text if soup.find('h1') else self.tr("Unknown Album"))
                    folder_path = self.create_folder(os.path.join(base_folder, folder_name))
                else:
                    folder_path = base_folder  # Use the base folder directly

                media_urls = []
                seen_urls = set() 

                # --- vídeos ---
                if download_videos:
                    for video in soup.find_all('video'):
                        source = video.find('source')
                        if source:
                            abs_video_src = urljoin(page_url, source['src'])
                            if abs_video_src in seen_urls:      # ya lo tenemos
                                continue
                            seen_urls.add(abs_video_src)
                            video_name = os.path.join(
                                folder_path,
                                self.clean_filename(os.path.basename(abs_video_src))
                            )
                            media_urls.append(
                                (abs_video_src, video_name, 'Video')
                            )

                # --- imágenes ---
                if download_images:
                    for div in soup.select('div.img'):
                        img = div.find('img', attrs={'data-src': True})
                        if img:
                            abs_img_src = urljoin(page_url, img['data-src'])
                            if abs_img_src in seen_urls:
                                continue
                            seen_urls.add(abs_img_src)
                            img_name = os.path.join(
                                folder_path,
                                self.clean_filename(os.path.basename(abs_img_src))
                            )
                            media_urls.append(
                                (abs_img_src, img_name, 'Image')
                            )

                self.total_files += len(media_urls)
                futures = [self.executor.submit(self.download_file, url, file_path, resource_type, str(uuid.uuid4())) for url, file_path, resource_type in media_urls]
                for future in as_completed(futures):
                    if self.cancel_requested:
                        self.log(self.tr("Cancelling remaining downloads."))
                        break
                    future.result()

                self.log(self.tr("Album download complete: {folder_name}", folder_name=folder_name) if not self.direct_download else self.tr("Album download complete"))
                if not self.is_profile_download:
                    self.enable_widgets_callback()
            else:
                self.log(self.tr("Error accessing page: {page_url}, status code: {status_code}", page_url=page_url, status_code=response.status_code))
                if not self.is_profile_download:
                    self.enable_widgets_callback()
        finally:
            if not self.is_profile_download:
                self.enable_widgets_callback()
            self.export_logs()

    def process_profile_page(self, url, download_folder, download_images, download_videos):
        try:
            if self.cancel_requested:
                return
            self.log(self.tr("Processing profile URL: {url}", url=url))
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                username = soup.find('h1', class_='username').text.strip() if soup.find('h1', class_='username') else self.tr("Unknown Profile")
                base_folder = self.create_folder(os.path.join(download_folder, self.clean_filename(username)))

                album_links = soup.find_all('a', class_='album-link')
                for album_link in album_links:
                    album_href = album_link.get('href')
                    album_full_url = urljoin(url, album_href)
                    self.process_album_page(album_full_url, base_folder, download_images, download_videos)

                self.log(self.tr("Profile download complete: {username}", username=username))
                self.enable_widgets_callback()
            else:
                self.log(self.tr("Error accessing page: {url}, status code: {status_code}", url=url, status_code=response.status_code))
                self.enable_widgets_callback()
        finally:
            if not self.is_profile_download:
                self.enable_widgets_callback()
            self.export_logs()

    def export_logs(self):
        log_folder = "resources/config/logs/"
        Path(log_folder).mkdir(parents=True, exist_ok=True)
        log_file_path = Path(log_folder) / f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(log_file_path, 'w') as file:
                file.write("\n".join(self.log_messages))
            self.log(self.tr("Logs exported successfully to {path}", path=log_file_path))
        except Exception as e:
            self.log(self.tr(f"Failed to export logs: {e}"))
