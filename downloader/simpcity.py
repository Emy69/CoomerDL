import cloudscraper
import time
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

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

    def save_cookies_to_file(self, cookies, file_path):
        """ Guarda las cookies en un archivo JSON. """
        with open(file_path, 'w') as file:
            json.dump(cookies, file)
        self.log(f"Cookies guardadas en {file_path}")

    def load_cookies_from_file(self, file_path):
        """ Carga las cookies desde un archivo JSON. """
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                cookies = json.load(file)
            self.log(f"Cookies cargadas desde {file_path}")
            return cookies
        else:
            self.log(f"No se encontró el archivo de cookies: {file_path}")
            return None

    def get_cookies_with_selenium(self, url, cookies_file='resources/config/cookies.json'):
        # Cargar cookies desde el archivo si existe
        cookies = self.load_cookies_from_file(cookies_file)
        if cookies:
            return cookies

        # Abrir el navegador para que el usuario inicie sesión
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        self.log("Por favor, inicia sesión en el navegador abierto.")

        try:
            # Esperar hasta que un elemento con el selector CSS '.message-content.js-messageContent' esté presente
            WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.message-content.js-messageContent'))
            )
            cookies = driver.get_cookies()
        except Exception as e:
            self.log(f"Error al esperar el inicio de sesión: {e}")
            cookies = None
        finally:
            driver.quit()

        if cookies:
            # Guardar cookies en un archivo
            self.save_cookies_to_file(cookies, cookies_file)
        return cookies

    def set_cookies_in_scraper(self, cookies):
        for cookie in cookies:
            self.scraper.cookies.set(cookie['name'], cookie['value'])

    def fetch_page(self, url):
        """ Realiza una solicitud GET usando cloudscraper. """
        try:
            # Obtener cookies con Selenium solo si no están guardadas
            cookies = self.get_cookies_with_selenium(url)
            self.set_cookies_in_scraper(cookies)

            response = self.scraper.get(url)
            if response.status_code == 403:
                self.log("Acceso prohibido. Intentando de nuevo...")
                time.sleep(5)  # Esperar antes de reintentar
                response = self.scraper.get(url)
            return response
        except requests.exceptions.RequestException as e:
            self.log(f"Error al acceder a {url}: {e}")
            return None

    def download_images_from_simpcity(self, url):
        """ Descarga las imágenes desde una URL específica de SimpCity. """
        self.log(f"Accediendo a {url}")
        
        # Procesar solo la página proporcionada
        self.process_page(url)

        if not self.cancel_requested:
            self.log("Descarga de la página completada.")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()

    def sanitize_folder_name(self, name):
        # Reemplaza caracteres no válidos con un guion bajo
        return re.sub(r'[<>:"/\\|?*]', '_', name)

    def process_page(self, url):
        """ Procesa una página específica para descargar imágenes. """
        response = self.fetch_page(url)
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Obtener el título de la página
            title_element = soup.find('h1')
            if title_element:
                for a in title_element.find_all('a'):
                    a.extract()
                folder_name = title_element.get_text(strip=True)
                folder_name = self.sanitize_folder_name(folder_name)  # Sanitizar el nombre de la carpeta
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
        
        response = self.scraper.get(imagen_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            header_content_right = soup.find('div', class_='header-content-right')
            
            if header_content_right:
                download_link = header_content_right.find('a', class_='btn-download')
                if download_link and 'href' in download_link.attrs:
                    image_url = download_link['href']
                    image_name = os.path.basename(urlparse(image_url).path)
                    destination_path = os.path.join(download_folder, image_name)
                    
                    # Asegúrate de que el directorio existe antes de guardar
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    
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
        response = self.scraper.get(image_url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            if self.update_progress_callback:
                self.update_progress_callback(0, total_size, file_id=file_id, file_path=path)

            with open(path, 'wb') as file:
                for chunk in response.iter_content(1024 * 10):  # Leer en chunks de 10KB
                    if self.cancel_requested:
                        self.log("Descarga cancelada durante la escritura del archivo.")
                        file.close()
                        os.remove(path)
                        return
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    # Actualizar el progreso cada 100KB descargados
                    if downloaded_size % (1024 * 100) == 0 and self.update_progress_callback:
                        self.update_progress_callback(downloaded_size, total_size, file_id=file_id, file_path=path)

            self.log(f"Imagen descargada: {path}")
            self.completed_files += 1
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)
        else:
            self.log(f"Error al descargar la imagen: {image_url}")
