import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue

class SimpCity:
    def __init__(self, download_folder, max_workers=5, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None):
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
        self.download_queue = queue.Queue()

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def request_cancel(self):
        """ Solicita cancelar las descargas en curso. """
        self.cancel_requested = True
        self.log("Descarga cancelada por el usuario.")

    def start_download_thread(self, url):
        """ Inicia un hilo para manejar las descargas. """
        download_thread = threading.Thread(target=self.download_images_from_simpcity, args=(url,))
        download_thread.start()

    def download_images_from_simpcity(self, url):
        """ Descarga las imágenes desde todas las páginas de una URL de SimpCity. """
        # Descargar la página inicial
        self.process_page(url)

        # Comenzar la paginación
        page_number = 1
        while not self.cancel_requested:
            paginated_url = f"{url.rstrip('/')}/page-{page_number}"
            self.log(f"Accediendo a {paginated_url}")
            
            # Mover la solicitud de red a un hilo separado
            response = self.fetch_page(paginated_url)
            if response is None or response.status_code != 200:
                self.log(f"No se encontró la página {paginated_url}. Deteniendo la búsqueda.")
                break
            
            self.process_page(paginated_url)
            page_number += 1

        if not self.cancel_requested:
            self.log("Todas las descargas han terminado.")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()

    def fetch_page(self, url):
        """ Realiza una solicitud GET en un hilo separado. """
        try:
            response = requests.get(url)
            return response
        except requests.RequestException as e:
            self.log(f"Error al acceder a {url}: {e}")
            return None

    def process_page(self, url):
        """ Procesa una página específica para descargar imágenes. """
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Obtener el título de la página
            title_element = soup.find('h1')
            if title_element:
                for a in title_element.find_all('a'):
                    a.extract()
                folder_name = title_element.get_text(strip=True)
            else:
                folder_name = 'SimpCity_Download'
            
            download_folder = os.path.join(self.download_folder, folder_name)
            os.makedirs(download_folder, exist_ok=True)
            
            message_inners = soup.find_all('div', class_='message-inner')
            
            for div in message_inners:
                bbwrapper = div.find('div', class_='bbWrapper')
                if bbwrapper:
                    links = bbwrapper.find_all('a', class_='link--external')
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = []
                        for link in links:
                            if 'href' in link.attrs:
                                imagen_url = link['href']
                                if imagen_url not in self.descargadas:
                                    futures.append(executor.submit(self.download_image_from_link, imagen_url, download_folder))
                                    self.descargadas.add(imagen_url)
                                else:
                                    self.log(f"Imagen ya descargada, saltando: {imagen_url}")
                        
                        # Esperar a que todas las descargas del bbWrapper terminen
                        for future in as_completed(futures):
                            try:
                                future.result()  # Manejar excepciones aquí si es necesario
                            except Exception as e:
                                self.log(f"Error al descargar: {e}")
        else:
            self.log(f"Error al acceder a {url}: Código de estado {response.status_code}")

    def start_download_workers(self):
        """ Inicia los trabajadores para descargar imágenes. """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            while not self.download_queue.empty():
                imagen_url, download_folder = self.download_queue.get()
                futures.append(executor.submit(self.download_image_from_link, imagen_url, download_folder))
                
                # Limitar el número de tareas en progreso
                if len(futures) >= self.max_workers:
                    for future in as_completed(futures):
                        if self.cancel_requested:
                            self.log("Descarga cancelada durante el proceso.")
                            break
                        try:
                            future.result()  # Manejar excepciones aquí si es necesario
                        except Exception as e:
                            self.log(f"Error al descargar: {e}")
                    futures = []  # Resetear la lista de futuros para el siguiente lote

            # Asegurarse de que todas las tareas restantes se completen
            for future in as_completed(futures):
                if self.cancel_requested:
                    self.log("Descarga cancelada durante el proceso.")
                    break
                try:
                    future.result()  # Manejar excepciones aquí si es necesario
                except Exception as e:
                    self.log(f"Error al descargar: {e}")

    def download_image_from_link(self, imagen_url, download_folder):
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
                    destination_path = os.path.join(download_folder, image_name)
                    
                    self.save_image(image_url, destination_path, file_id=image_url)
        else:
            self.log(f"Error al acceder a {imagen_url}: Código de estado {response.status_code}")

    def save_image(self, image_url, path, file_id=None):
        """ Guarda la imagen desde la URL al destino especificado. """
        if os.path.exists(path):
            self.log(f"Archivo ya existe, saltando: {path}")
            self.completed_files += 1
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)
            return

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
