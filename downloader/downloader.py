import re
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import threading
from concurrent.futures import ThreadPoolExecutor
import time  

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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        self.media_counter = 0 
        self.download_images = download_images
        self.download_videos = download_videos  
        self.session = requests.Session()
        self.image_executor = ThreadPoolExecutor(max_workers=3)
        self.video_executor = ThreadPoolExecutor(max_workers=2)

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def request_cancel(self):
        self.cancel_requested.set() 
        self.log("Download cancelled.")
        if self.enable_widgets_callback:
            self.enable_widgets_callback()
        self.shutdown_executors()

    def shutdown_executors(self):
        self.image_executor.shutdown(wait=False)
        self.video_executor.shutdown(wait=False)
        if self.enable_widgets_callback:
            self.enable_widgets_callback()

    def safe_request(self, url, max_retries=5):
        retry_wait = 1  # Comienza con 1 segundo
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, stream=True, headers=self.headers)
                response.raise_for_status()
                return response
            except (requests.ConnectionError, requests.HTTPError, requests.TooManyRedirects) as e:
                self.log(f"Retry {attempt + 1}: Error {e}, waiting {retry_wait} seconds before retrying.")
                time.sleep(retry_wait)
                retry_wait *= 2  # Incrementa el tiempo de espera exponencialmente
            except requests.exceptions.RequestException as e:
                self.log(f"Non-retryable error: {e}")
                break
        return None

    def generate_image_links(self, start_url):
        image_urls = []
        folder_name = ""
        user_id = ""
        try:
            response = self.session.get(start_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            base_url = "https://coomer.su/" if "coomer.su" in start_url else "https://kemono.su/"
            
            user_id = start_url.split('/user/')[1].split('/')[0].split('?')[0]  
            
            if "/post/" in start_url:
                post_id = start_url.split("/post/")[-1].split('?')[0]  
                image_urls.append(start_url)
            else:
                name_element = soup.find(attrs={"itemprop": "name"})
                if name_element:
                    folder_name = name_element.text.strip()
                posts = soup.find_all('article', class_='post-card post-card--preview')
                for idx, post in enumerate(posts):
                    data_id = post.get('data-id')
                    data_service = post.get('data-service')
                    data_user = post.get('data-user')
                    if data_id and data_service and data_user:
                        image_url = f"{base_url}{data_service}/user/{data_user}/post/{data_id}"
                        image_urls.append(image_url)

        except Exception as e:
            self.log(f"Error collecting links: {e}")
        return image_urls, folder_name, user_id

    def process_media_element(self, element, page_idx, media_idx, page_url, media_type, user_id):
        if self.cancel_requested.is_set():
            return

        media_url = element.get('href')
        download_name = element.get('download')
        
        if media_url.startswith('//'):
            media_url = "https:" + media_url
        elif not media_url.startswith('http'):
            base_url = "https://coomer.su/" if "coomer.su" in page_url else "https://kemono.su/"
            media_url = urljoin(base_url, media_url)
        
        self.log(f"Starting download: {media_type} #{media_idx+1} from {page_url}")
        
        try:
            response = self.safe_request(media_url)
            if response is None:
                self.log(f"Failed to download after multiple retries: {media_url}")
                return

            media_folder = os.path.join(self.download_folder, user_id, "videos" if media_type == "video" else "images")
            os.makedirs(media_folder, exist_ok=True)
            
            filename = download_name if download_name else os.path.basename(media_url).split('?')[0]
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = os.path.join(media_folder, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=524288):
                    if self.cancel_requested.is_set():
                        f.close()
                        os.remove(filepath)
                        self.log(f"Download cancelled for: {media_type} #{media_idx+1} from {page_url}")
                        break
                    f.write(chunk)
            
            if not self.cancel_requested.is_set():
                self.log(f"Download success: {media_type} #{media_idx+1} from {page_url}")
        
        except Exception as e:
            self.log(f"Error downloading: {e}")

    def download_media(self, image_urls, user_id, download_images=True, download_videos=True):
        futures = []
        try:
            for i, page_url in enumerate(image_urls):
                if self.cancel_requested.is_set():
                    break

                page_response = self.session.get(page_url, headers=self.headers)
                page_soup = BeautifulSoup(page_response.content, 'html.parser')

                if download_images:
                    image_elements = page_soup.select('div.post__thumbnail a.fileThumb')
                    for idx, image_element in enumerate(image_elements):
                        futures.append(self.image_executor.submit(self.process_media_element, image_element, i, idx, page_url, "image", user_id))

                if download_videos:
                    video_elements = page_soup.select('ul.post__attachments li.post__attachment a.post__attachment-link')
                    for idx, video_element in enumerate(video_elements):
                        futures.append(self.video_executor.submit(self.process_media_element, video_element, i, idx, page_url, "video", user_id))

        except Exception as e:
            self.log(f"Error during download: {e}")
        finally:
            # Esperar a que todos los futures se completen
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    self.log(f"Error in download task: {e}")
            
            self.shutdown_executors()  
            # Verificar si la lista de futures no está vacía para asegurar que se procesaron descargas
            if futures:
                self.log("All downloads completed or cancelled.")