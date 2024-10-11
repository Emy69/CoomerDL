import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

class SimpCity:
    def __init__(self, download_folder, max_workers=5, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None):
        """
        Inicializa la clase SimpCity con capacidad de descargas concurrentes.
        
        :param download_folder: Directorio donde se guardarán los archivos descargados.
        :param max_workers: Número máximo de descargas simultáneas.
        :param log_callback: Función para enviar mensajes de log a la interfaz.
        :param enable_widgets_callback: Función para habilitar la interfaz después de la descarga.
        :param update_progress_callback: Función para actualizar el progreso de cada archivo.
        :param update_global_progress_callback: Función para actualizar el progreso global de la descarga.
        """
        self.download_folder = download_folder
        self.max_workers = max_workers
        self.descargadas = set()
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.cancel_requested = False
        self.total_files = 0
        self.completed_files = 0

    def log(self, message):
        """ Envia mensajes de log a través del callback. """
        if self.log_callback:
            self.log_callback(message)

    def request_cancel(self):
        """ Solicita cancelar las descargas en curso. """
        self.cancel_requested = True
        self.log("Descarga cancelada por el usuario.")

    def download_images_from_simpcity(self, url):
        """ Descarga las imágenes desde una URL de SimpCity. """
        if self.cancel_requested:
            self.log("Descarga cancelada antes de comenzar.")
            return

        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            message_inners = soup.find_all('div', class_='message-inner')
            media_urls = []
            
            for div in message_inners:
                bbwrapper = div.find('div', class_='bbWrapper')
                if bbwrapper:
                    links = bbwrapper.find_all('a', class_='link--external')
                    for link in links:
                        if 'href' in link.attrs:
                            imagen_url = link['href']
                            if imagen_url not in self.descargadas:
                                media_urls.append(imagen_url)
                                self.descargadas.add(imagen_url)
                            else:
                                self.log(f"Imagen ya descargada, saltando: {imagen_url}")
            
            self.total_files = len(media_urls)
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.download_image_from_link, url, idx) for idx, url in enumerate(media_urls)]
                for future in as_completed(futures):
                    if self.cancel_requested:
                        self.log("Descarga cancelada durante el proceso.")
                        break
                    future.result()  # Procesa cualquier excepción en los hilos
            
            if not self.cancel_requested:
                self.log("Todas las descargas han terminado.")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()
        else:
            self.log(f"Error al acceder a {url}: Código de estado {response.status_code}")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()

    def download_image_from_link(self, imagen_url, index):
        """ Descarga una imagen desde el enlace especificado. """
        if self.cancel_requested:
            self.log("Descarga cancelada.")
            return
        
        response = requests.get(imagen_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            header_content_right = soup.find('div', class_='header-content-right')
            
            if header_content_right:
                download_link = header_content_right.find('a', class_='btn-download')
                if download_link and 'href' in download_link.attrs:
                    image_url = download_link['href']
                    image_name = os.path.basename(urlparse(image_url).path)
                    destination_path = os.path.join(self.download_folder, 'download', image_name)
                    
                    self.save_image(image_url, destination_path, file_id=image_url)
        else:
            self.log(f"Error al acceder a {imagen_url}: Código de estado {response.status_code}")

    def save_image(self, image_url, path, file_id=None):
        """ Guarda la imagen desde la URL al destino especificado. """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            if self.update_progress_callback:
                self.update_progress_callback(0, total_size, file_id=file_id, file_path=path)

            with open(path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    if self.cancel_requested:
                        self.log("Descarga cancelada durante la escritura del archivo.")
                        file.close()
                        os.remove(path)
                        return
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    if self.update_progress_callback:
                        self.update_progress_callback(downloaded_size, total_size, file_id=file_id, file_path=path)

            self.log(f"Imagen descargada: {path}")
            self.completed_files += 1
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)
        else:
            self.log(f"Error al descargar la imagen: {image_url}")
