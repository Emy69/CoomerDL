from tkinter import messagebox
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import time

class Downloader:
    def __init__(self, download_folder, translations, log_callback=None, enable_widgets_callback=None, update_speed_callback=None):
        self.download_folder = download_folder
        self.translations = translations  # Diccionario de traducciones para el idioma actual
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_speed_callback = update_speed_callback
        self.cancel_requested = False

    def log(self, message_key, **kwargs):
        # Construye y envía un mensaje de log utilizando la clave del mensaje y los argumentos proporcionados.
        if self.log_callback is not None:
            message_template = self.translations[message_key]
            message = message_template.format(**kwargs)
            self.log_callback(message)

    def request_cancel(self):
        self.cancel_requested = True   

    def generate_image_links(self, start_url):
        image_urls = []
        folder_name = ""
        try:
            response = requests.get(start_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Determinar el dominio base de la URL proporcionada
            base_url = "https://coomer.su/" if "coomer.su" in start_url else "https://kemono.su/"
            
            # Intenta obtener el nombre del elemento con itemprop="name"
            name_element = soup.find(attrs={"itemprop": "name"})
            if name_element:
                folder_name = name_element.text.strip()

            # Ajustar la búsqueda de los posts según el sitio web
            posts = soup.find_all('article', class_='post-card post-card--preview')
            for post in posts:
                data_id = post.get('data-id')
                data_service = post.get('data-service')
                data_user = post.get('data-user')

                if data_id and data_service and data_user:
                    image_url = f"{base_url}{data_service}/user/{data_user}/post/{data_id}"
                    image_urls.append(image_url)
        except Exception as e:
            if self.log_callback is not None:
                self.log("log_message_error_collecting_links", e=str(e))

        return image_urls, folder_name

    def process_media_element(self, element, page_idx, media_idx, page_url, media_type):
        if self.cancel_requested:
            return

        media_url = element.get('src') or element.get('data-src') or element.get('href')
        if media_url.startswith('//'):
            media_url = "https:" + media_url
        elif not media_url.startswith('http'):
            base_url = "https://coomer.su/" if "coomer.su" in page_url else "https://kemono.su/"
            media_url = urljoin(base_url, media_url)

        # Mensaje de inicio de descarga
        if self.log_callback is not None:
            self.log("log_message_start_download", media_type=media_type, page_idx=page_idx+1, media_idx=media_idx+1, page_url=page_url)

        try:
            with requests.get(media_url, stream=True) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                start_time = time.time()
                data_downloaded = 0
                extension = media_url.split('.')[-1].split('?')[0]
                filename = f"{media_type}_{page_idx}_{media_idx}.{extension}"
                filepath = os.path.join(self.download_folder, filename)

                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if self.cancel_requested:
                            break
                        if chunk:
                            f.write(chunk)
                            data_downloaded += len(chunk)
                            elapsed_time = time.time() - start_time
                            # Asegurarse de que elapsed_time no sea cero antes de calcular la velocidad
                            if elapsed_time > 0:
                                speed_kb_s = (data_downloaded / elapsed_time) / 1024  # velocidad en KB/s
                                if self.update_speed_callback:
                                    self.update_speed_callback(speed_kb_s)
                            else:
                                # Si elapsed_time es cero, evitar la división por cero
                                if self.update_speed_callback:
                                    self.update_speed_callback(0)
        except requests.exceptions.RequestException as e:
            if self.log_callback is not None:
                self.log("log_message_error_download", media_url=media_url, e=str(e))

        if not self.cancel_requested and self.log_callback is not None:
            self.log("log_message_success_download", media_type=media_type, page_idx=page_idx+1, media_idx=media_idx+1, page_url=page_url)

    def download_images(self, image_urls, download_images=True, download_videos=True):
        try:
            for i, page_url in enumerate(image_urls):
                if self.cancel_requested:
                    break

                page_response = requests.get(page_url)
                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                media_found = False  # Indicador para saber si se encontraron medios

                if download_images:
                    # Procesa imágenes
                    image_elements = page_soup.select('div.post__thumbnail img')
                    for idx, image_element in enumerate(image_elements):
                        self.process_media_element(image_element, i, idx, page_url, "imagen")
                        media_found = True

                if download_videos:
                    # Procesa videos
                    video_elements = page_soup.select('ul.post__attachments li.post__attachment a.post__attachment-link')
                    for idx, video_element in enumerate(video_elements):
                        self.process_media_element(video_element, i, idx, page_url, "video")
                        media_found = True

                # Si no se encontraron medios, se notifica mediante el callback
                if not media_found:
                    if self.log_callback is not None:
                        self.log("log_message_no_media", page_url=page_url)

            if self.log_callback is not None:
                self.log("log_message_download_complete")
        except Exception as e:
            if self.log_callback is not None:
                self.log("log_message_error_during_download", e=str(e))
        finally:
            self.cancel_requested = False
            if self.enable_widgets_callback is not None:
                self.enable_widgets_callback()