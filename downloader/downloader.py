import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

class Downloader:
    def __init__(self, download_folder, log_callback=None, enable_widgets_callback=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback

    def generate_image_links(self, start_url):
        image_urls = []
        try:
            response = requests.get(start_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.find_all('article', class_='post-card post-card--preview')

            for post in posts:
                data_id = post.get('data-id')
                data_service = post.get('data-service')
                data_user = post.get('data-user')

                if data_id and data_service and data_user:
                    image_url = f"https://coomer.su/{data_service}/user/{data_user}/post/{data_id}"
                    image_urls.append(image_url)

        except Exception as e:
            if self.log_callback is not None:
                self.log_callback(f"Error durante la recopilación de links: {str(e)}")
        return image_urls


    def process_media_element(self, element, page_idx, media_idx, page_url, media_type):
        media_url = element.get('src') or element.get('data-src') or element.get('href')
        if media_url.startswith('//'):
            media_url = "https:" + media_url
        elif not media_url.startswith('http'):
            media_url = urljoin("https://coomer.su/", media_url)
        media_data = requests.get(media_url).content
        extension = media_url.split('.')[-1].split('?')[0]
        filename = f"{media_type}_{page_idx}_{media_idx}.{extension}"
        filepath = os.path.join(self.download_folder, filename)
        with open(filepath, 'wb') as file:
            file.write(media_data)
        #self.add_log_message(f"Descargado {media_type} {page_idx+1}-{media_idx+1}")
        if self.log_callback is not None:
                self.log_callback(f"Descargado {media_type} {page_idx+1}-{media_idx+1} de URL: {page_url}")

    def download_images(self, image_urls):
        try:
            if not image_urls:  # Si no hay URLs para procesar, actualiza el log directamente.
                if self.log_callback is not None:
                    self.log_callback("No se encontraron URLs para descargar.")
                return

            for i, page_url in enumerate(image_urls):
                page_response = requests.get(page_url)
                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                
                # Procesa imágenes
                image_elements = page_soup.select('div.post__thumbnail img')
                for idx, image_element in enumerate(image_elements):
                    self.process_media_element(image_element, i, idx, page_url, "imagen")

                # Procesa videos
                video_elements = page_soup.select('ul.post__attachments li.post__attachment a.post__attachment-link')
                for idx, video_element in enumerate(video_elements):
                    self.process_media_element(video_element, i, idx, page_url, "video")

                if not image_elements and not video_elements:
                    if self.log_callback is not None:
                        self.log_callback(f"No se encontraron medios en URL: {page_url}")
            if self.log_callback is not None:
                self.log_callback("Descarga Terminada.")
        except Exception as e:
            if self.log_callback is not None:
                self.log_callback(f"Error durante la descarga: {str(e)}")
        finally:
            if self.enable_widgets_callback is not None:
                self.enable_widgets_callback() 

    
    

