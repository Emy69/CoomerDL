import hashlib
import os
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
import uuid
import re
import threading

class BunkrDownloader:
    def __init__(self, download_folder, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, headers=None, max_workers=5, translations=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Referer': 'https://bunkr.site/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.cancel_requested = False  # Flag to indicate if a cancellation request has been made
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # Thread pool executor for concurrent downloads
        self.total_files = 0
        self.completed_files = 0
        self.max_downloads = 5  # Valor por defecto
        self.log_messages = []  # Cola para almacenar mensajes de log
        self.notification_interval = 10  # Intervalo de notificación en segundos
        self.start_notification_thread()
        self.translations = translations or {}  

    def start_notification_thread(self):
        def notify_user():
            while not self.cancel_requested:
                if self.log_messages:
                    # Enviar todos los mensajes acumulados
                    if self.log_callback:
                        self.log_callback("\n".join(self.log_messages))
                    self.log_messages.clear()
                time.sleep(self.notification_interval)

        # Iniciar un hilo para notificaciones periódicas
        notification_thread = threading.Thread(target=notify_user, daemon=True)
        notification_thread.start()

    def tr(self, key):
        # Obtener la traducción para la clave dada
        return self.translations.get(key, key)

    def log(self, message_key, url=None):
        message = self.tr(message_key)
        domain = urlparse(url).netloc if url else "General"
        full_message = f"{domain}: {message}"
        self.log_messages.append(full_message)  # Agregar mensaje a la cola

    def request_cancel(self):
        self.cancel_requested = True
        self.log("Download has been cancelled.")
        self.shutdown_executor()

    def shutdown_executor(self):
        self.executor.shutdown(wait=False)
        self.log("Executor shut down.")

    def clean_filename(self, filename):
        return re.sub(r'[<>:"/\\|?*\u200b]', '_', filename)
    
    def get_consistent_folder_name(self, url, default_name):
        # Genera un hash de la URL para crear un nombre único y consistente
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        folder_name = f"{default_name}_{url_hash}"
        return self.clean_filename(folder_name)

    def download_file(self, url_media, ruta_carpeta, file_id):
        if self.cancel_requested:
            self.log("Descarga cancelada", url=url_media)
            return

        file_name = os.path.basename(urlparse(url_media).path)
        file_path = os.path.join(ruta_carpeta, file_name)
        
        if os.path.exists(file_path):
            self.log(f"El archivo ya existe, omitiendo: {file_path}")
            self.completed_files += 1
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)
            return

        max_attempts = 3
        delay = 1
        for attempt in range(max_attempts):
            try:
                self.log(f"Intentando descargar {url_media} (Intento {attempt + 1}/{max_attempts})")
                response = self.session.get(url_media, headers=self.headers, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                # Descargar el archivo en fragmentos
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=65536):  # Fragmentos de 64KB
                        if self.cancel_requested:
                            self.log("Descarga cancelada durante la descarga del archivo.", url=url_media)
                            file.close()
                            os.remove(file_path)
                            return
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        if self.update_progress_callback:
                            self.update_progress_callback(downloaded_size, total_size, file_id=file_id, file_path=file_path)

                self.log("Archivo descargado", url=url_media)
                # Notificar al usuario al completar la descarga
                if self.log_callback:
                    self.log_callback(f"Descarga completada: {file_name}")
                self.completed_files += 1
                if self.update_global_progress_callback:
                    self.update_global_progress_callback(self.completed_files, self.total_files)
                break
            except requests.RequestException as e:
                if response.status_code == 429:
                    self.log(f"Límite de tasa excedido. Reintentando después de {delay} segundos.")
                    time.sleep(delay)
                    delay *= 2  # Retroceso exponencial para limitación de tasa
                else:
                    self.log(f"Error al descargar de {url_media}: {e}. Intento {attempt + 1} de {max_attempts}", url=url_media)
                    if attempt < max_attempts - 1:
                        time.sleep(3)
    
    def descargar_post_bunkr(self, url_post):
        try:
            self.log(f"Iniciando descarga para el post: {url_post}")
            response = self.session.get(url_post, headers=self.headers)
            self.log(f"Código de estado de la respuesta: {response.status_code} para {url_post}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extraer y sanitizar el nombre de la carpeta para el post
                file_name_tag = soup.find('h1', {'class': 'truncate'})
                if file_name_tag:
                    file_name = file_name_tag.text.strip()
                    file_name = self.clean_filename(file_name)[:50]  # Limitar a 50 caracteres
                else:
                    file_name = "bunkr_post"
                
                folder_name = self.get_consistent_folder_name(url_post, file_name)
                ruta_carpeta = os.path.join(self.download_folder, folder_name)
                os.makedirs(ruta_carpeta, exist_ok=True)

                media_urls = []
                self.log(f"Procesando URL de la página de medios: {url_post}")

                # Buscar imágenes
                media_divs = soup.find_all('figure', {'class': 'relative rounded-lg overflow-hidden flex justify-center items-center aspect-video bg-soft'})
                for div in media_divs:
                    img_tags = div.find_all('img')
                    for img_tag in img_tags:
                        if 'src' in img_tag.attrs:
                            img_url = img_tag['src']
                            self.log(f"URL de imagen encontrada: {img_url}")
                            media_urls.append((img_url, ruta_carpeta))

                # Buscar videos usando el nuevo método
                video_divs = soup.find_all('div', {'class': 'flex w-full md:w-auto gap-4'})
                self.log(f"Se encontraron {len(video_divs)} divs de video.")
                for video_div in video_divs:
                    self.log("Buscando enlace de página de descarga en el div de video.")
                    download_page_link = video_div.find('a', {'class': 'btn btn-main btn-lg rounded-full px-6 font-semibold flex-1 ic-download-01 ic-before before:text-lg'})
                    if download_page_link and 'href' in download_page_link.attrs:
                        video_page_url = download_page_link['href']
                        self.log(f"URL de la página de descarga encontrada: {video_page_url}. Accediendo ahora.")

                        # Acceder a la página del video para obtener el enlace de descarga real
                        video_page_response = self.session.get(video_page_url, headers=self.headers)
                        self.log(f"Estado de la respuesta de la página de video: {video_page_response.status_code} para {video_page_url}")
                        
                        if video_page_response.status_code == 200:
                            video_page_soup = BeautifulSoup(video_page_response.text, 'html.parser')
                            self.log("Buscando enlace de descarga real en la página de video.")
                            download_link = video_page_soup.find('a', {'class': 'btn btn-main btn-lg rounded-full px-6 font-semibold ic-download-01 ic-before before:text-lg'})
                            if download_link and 'href' in download_link.attrs:
                                video_url = download_link['href']
                                self.log(f"URL de descarga de video encontrada: {video_url}")
                                media_urls.append((video_url, ruta_carpeta))
                            else:
                                self.log(f"No se encontró enlace de descarga en la página de video: {video_page_url}")
                        else:
                            self.log(f"Error al acceder a la página de video: {video_page_url} con estado {video_page_response.status_code}")

                # Debug: Imprimir todas las URLs de medios encontradas
                self.log(f"URLs de medios encontradas: {media_urls}")

                self.total_files = len(media_urls)
                if media_urls:  # Solo proceder si hay URLs para descargar
                    with ThreadPoolExecutor(max_workers=self.max_downloads) as executor:
                        futures = [executor.submit(self.download_file, url, folder, str(uuid.uuid4())) for url, folder in media_urls]
                        for future in as_completed(futures):
                            if self.cancel_requested:
                                self.log("Cancelando descargas restantes.")
                                break
                            future.result()

                self.log("Descarga iniciada para todos los medios.")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()
            else:
                self.log(f"Error al acceder al post {url_post}: Estado {response.status_code}")
        except Exception as e:
            self.log(f"Error al acceder al post {url_post}: {e}")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()

    def descargar_perfil_bunkr(self, url_perfil):
        try:
            self.log(f"Iniciando descarga para el perfil: {url_perfil}")
            response = self.session.get(url_perfil, headers=self.headers)
            self.log(f"Código de estado de la respuesta: {response.status_code} para {url_perfil}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extraer y sanitizar el nombre de la carpeta para el perfil
                file_name_tag = soup.find('h1', {'class': 'truncate'})
                if file_name_tag:
                    folder_name = file_name_tag.text.strip()
                else:
                    folder_name = "bunkr_profile"
                
                # Usar el nuevo método para obtener un nombre de carpeta consistente
                folder_name = self.get_consistent_folder_name(url_perfil, folder_name)
                ruta_carpeta = os.path.join(self.download_folder, folder_name)
                os.makedirs(ruta_carpeta, exist_ok=True)

                # Find media URLs in the profile
                media_urls = []
                grid_div = soup.find('div', {'class': 'grid gap-4 grid-cols-repeat [--size:11rem] lg:[--size:14rem] grid-images'})
                if grid_div:
                    links = grid_div.find_all('a', {'class': 'after:absolute after:z-10 after:inset-0'})
                    total_links = len(links)
                    for idx, link in enumerate(links):
                        if self.cancel_requested:
                            self.log("Cancelling remaining downloads.")
                            break

                        # Resolve relative URLs to full URLs
                        image_page_url = urljoin(url_perfil, link['href'])
                        self.log(f"Processing media page URL: {image_page_url}")

                        # Visit the page to get the media URL
                        image_response = self.session.get(image_page_url, headers=self.headers)
                        if image_response.status_code == 200:
                            image_soup = BeautifulSoup(image_response.text, 'html.parser')

                            # Search for image URL
                            media_tag = image_soup.select_one("figure.relative img[class='w-full h-full absolute opacity-20 object-cover blur-sm z-10']")
                            if media_tag and 'src' in media_tag.attrs:
                                media_url = urljoin(image_page_url, media_tag['src'])  # Resolve media URL
                                self.log(f"Found image URL: {media_url}")
                                media_urls.append((media_url, ruta_carpeta))

                            # Search for video URL
                            video_tag = image_soup.select_one("video#player")
                            if video_tag and 'src' in video_tag.attrs:
                                video_url = urljoin(image_page_url, video_tag['src'])  # Resolve video URL
                                self.log(f"Found video URL: {video_url}")
                                media_urls.append((video_url, ruta_carpeta))
                            else:
                                source_tag = video_tag.find('source') if video_tag else None
                                if source_tag and 'src' in source_tag.attrs:
                                    video_url = urljoin(image_page_url, source_tag['src'])  # Resolve video URL from source
                                    self.log(f"Found video URL from source: {video_url}")
                                    media_urls.append((video_url, ruta_carpeta))

                self.total_files = len(media_urls)
                futures = [self.executor.submit(self.download_file, url, folder, str(uuid.uuid4())) for url, folder in media_urls]
                
                # Only after all futures are done, enable widgets again
                for future in as_completed(futures):
                    if self.cancel_requested:
                        self.log("Cancelling remaining downloads.")
                        break
                    future.result()

                self.log("Download completed for all media.")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()  # Only enable after all downloads are done
            else:
                self.log(f"Failed to access the profile {url_perfil}: Status {response.status_code}")
        except Exception as e:
            self.log(f"Failed to access the profile {url_perfil}: {e}")
            if self.enable_widgets_callback:
                self.enable_widgets_callback()

    def set_max_downloads(self, max_downloads):
        self.max_downloads = max_downloads

