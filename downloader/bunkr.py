import os
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

class BunkrDownloader:
    def __init__(self, download_folder, log_callback=None, headers=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.cancel_requested = False

    def log(self, message, url=None):
        domain = urlparse(url).netloc if url else "General"
        full_message = f"{domain}: {message}"
        if self.log_callback:
            self.log_callback(full_message)

    def request_cancel(self):
        self.cancel_requested = True
        self.log("Download has been cancelled.")

    def download_file(self, url_media, ruta_carpeta):
        if self.cancel_requested:
            self.log("Download cancelled by the user.", url=url_media)
            return

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = self.session.get(url_media, headers=self.headers, stream=True)
                response.raise_for_status()
                file_name = os.path.basename(urlparse(url_media).path)
                file_path = os.path.join(ruta_carpeta, file_name)

                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if self.cancel_requested:
                            self.log("Download cancelled during the file download.", url=url_media)
                            file.close()
                            os.remove(file_path)
                            return
                        file.write(chunk)
                self.log(f"File downloaded: {file_name}", url=url_media)
                break
            except requests.RequestException as e:
                self.log(f"Failed to download from {url_media}: {e}. Attempt {attempt + 1} of {max_attempts}", url=url_media)
                if attempt < max_attempts - 1:
                    time.sleep(3)

    def descargar_perfil_bunkr(self, url_perfil):
        try:
            response = self.session.get(url_perfil, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                ruta_carpeta = os.path.join(self.download_folder, "Downloaded_Images")
                os.makedirs(ruta_carpeta, exist_ok=True)
                
                # Find all links that lead to image detail pages
                links = soup.select("div.grid-images_box a.grid-images_box-link")
                for link in links:
                    if self.cancel_requested:
                        self.log("Download cancelled by the user.")
                        break
                    image_page_url = link['href']
                    image_response = self.session.get(image_page_url, headers=self.headers)
                    if image_response.status_code == 200:
                        image_soup = BeautifulSoup(image_response.text, 'html.parser')
                        # Assuming the actual image is within a div with class 'lightgallery'
                        image_tag = image_soup.select_one("div.lightgallery img")
                        if image_tag and 'src' in image_tag.attrs:
                            img_url = image_tag['src']
                            self.download_file(img_url, ruta_carpeta)
                        else:
                            self.log("No image found at the page", url=image_page_url)
                    else:
                        self.log(f"Failed to access image page {image_page_url}: Status {image_response.status_code}")
                    
                    if self.cancel_requested:
                        break
            else:
                self.log(f"Failed to access the profile {url_perfil}: Status {response.status_code}")
        except Exception as e:
            self.log(f"Failed to access the profile {url_perfil}: {e}")

