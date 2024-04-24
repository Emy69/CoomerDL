import re
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import threading
from concurrent.futures import ThreadPoolExecutor

class Downloader:
    def __init__(self, download_folder, log_callback=None, download_images=True, 
                 download_videos=True, enable_widgets_callback=None, update_speed_callback=None, headers=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_speed_callback = update_speed_callback
        self.cancel_requested = False
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        self.media_counter = 0 
        self.download_images = download_images
        self.download_videos = download_videos  
        self.image_executor = ThreadPoolExecutor(max_workers=3)
        self.video_executor = ThreadPoolExecutor(max_workers=2)

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def request_cancel(self):
        self.cancel_requested = True
        self.log("Download cancelled.")

    def generate_image_links(self, start_url):
        image_urls = []
        folder_name = ""
        user_id = ""  
        try:
            response = requests.get(start_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            base_url = "https://coomer.su/" if "coomer.su" in start_url else "https://kemono.su/"
            name_element = soup.find(attrs={"itemprop": "name"})
            if name_element:
                folder_name = name_element.text.strip()
            posts = soup.find_all('article', class_='post-card post-card--preview')
            for post in posts:
                data_id = post.get('data-id')
                data_service = post.get('data-service')
                data_user = post.get('data-user')
                if data_id and data_service and data_user:
                    image_url = f"{base_url}{data_service}/user/{data_user}/post/{data_id}"
                    image_urls.append(image_url)
                    user_id = data_user  
        except Exception as e:
            self.log(f"Error collecting links: {e}")
        return image_urls, folder_name, user_id  

    def process_media_element(self, element, page_idx, media_idx, page_url, media_type, user_id):
        if self.cancel_requested:
            return
        media_url = element.get('src') or element.get('data-src') or element.get('href')
        if media_url.startswith('//'):
            media_url = "https:" + media_url
        elif not media_url.startswith('http'):
            base_url = "https://coomer.su/" if "coomer.su" in page_url else "https://kemono.su/"
            media_url = urljoin(base_url, media_url)
        self.log(f"Starting download: {media_type} #{media_idx+1} from {page_url}")
        try:
            with requests.get(media_url, stream=True, headers=self.headers) as r:
                r.raise_for_status()
                user_folder = os.path.join(self.download_folder, user_id)
                if not os.path.exists(user_folder):
                    os.makedirs(user_folder)
                filename = os.path.basename(media_url).split('?')[0]
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                filepath = os.path.join(user_folder, filename)
                # Aumentar el tamaño del chunk aquí
                chunk_size = 524288  # 512 KB, aumenta según sea necesario
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if self.cancel_requested:
                            break
                        f.write(chunk)
                self.log(f"Download success: {media_type} #{media_idx+1} from {page_url}")
        except Exception as e:
            self.log(f"Error downloading: {e}")

    def download_media(self, image_urls, user_id, download_images=True, download_videos=True):
        futures = []
        try:
            for i, page_url in enumerate(image_urls):
                if self.cancel_requested:
                    break

                page_response = requests.get(page_url)
                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                if download_images:
                    image_elements = page_soup.select('div.post__thumbnail img')
                    for idx, image_element in enumerate(image_elements):
                        futures.append(self.image_executor.submit(self.process_media_element, image_element, i, idx, page_url, "image", user_id))

                if download_videos:
                    video_elements = page_soup.select('ul.post__attachments li.post__attachment a.post__attachment-link')
                    for idx, video_element in enumerate(video_elements):
                        futures.append(self.video_executor.submit(self.process_media_element, video_element, i, idx, page_url, "video", user_id))

        except Exception as e:
            self.log(f"Error during download: {e}")
        finally:
            # Wait for all futures to complete
            for future in futures:
                future.result()  # This will block until the future has completed

            self.image_executor.shutdown()
            self.video_executor.shutdown()

            if not self.cancel_requested:
                self.log("Download complete.")
            
            if self.enable_widgets_callback:
                self.enable_widgets_callback()  
