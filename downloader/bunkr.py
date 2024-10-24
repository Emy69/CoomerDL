import hashlib
import os
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
import uuid
import re

class BunkrDownloader:
    def __init__(self, download_folder, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, headers=None, max_workers=5):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.cancel_requested = False  # Flag to indicate if a cancellation request has been made
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # Thread pool executor for concurrent downloads
        self.total_files = 0
        self.completed_files = 0

    def log(self, message, url=None):
        domain = urlparse(url).netloc if url else "General"
        full_message = f"{domain}: {message}"
        if self.log_callback:
            self.log_callback(full_message)

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
            self.log("Descarga cancelada por el usuario.", url=url_media)
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

                self.log(f"Archivo descargado: {file_name}", url=url_media)
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
                else:
                    file_name = "bunkr_post"
                
                # Usar el nuevo método para obtener un nombre de carpeta consistente
                folder_name = self.get_consistent_folder_name(url_post, file_name)
                ruta_carpeta = os.path.join(self.download_folder, folder_name)
                os.makedirs(ruta_carpeta, exist_ok=True)

                media_urls = []
                self.log(f"Processing media page URL: {url_post}")

                # Buscar imágenes
                media_divs = soup.find_all('figure', {'class': 'relative rounded-lg overflow-hidden flex justify-center items-center aspect-video bg-soft'})
                print(f"Searching for images in {len(media_divs)} <figure> tags.")
                for div in media_divs:
                    img_tags = div.find_all('img')
                    for img_tag in img_tags:
                        if 'src' in img_tag.attrs:
                            img_url = img_tag['src']
                            self.log(f"Found image URL: {img_url}")
                            media_urls.append((img_url, ruta_carpeta))

                # Buscar el video en la estructura del post
                video_divs = soup.find_all('div', {'class': 'plyr__video-wrapper'})
                print(f"Searching for videos in {len(video_divs)} <div> tags.")
                for video_div in video_divs:
                    print(f"Checking video div: {video_div}")  # Detalle de cada div encontrado
                    video_tag = video_div.find('video', {'id': 'player'})
                    if video_tag:
                        print(f"Video tag found: {video_tag}")

                        # Verificar si hay un src en el video
                        if 'src' in video_tag.attrs:
                            video_url = video_tag['src']
                            self.log(f"Found video URL: {video_url}")
                            media_urls.append((video_url, ruta_carpeta))
                        else:
                            source_tag = video_tag.find('source')
                            if source_tag and 'src' in source_tag.attrs:
                                video_url = source_tag['src']
                                self.log(f"Found video URL from source: {video_url}")
                                media_urls.append((video_url, ruta_carpeta))
                            else:
                                print("No video URL found in video tag or source tag.")

                # Debug print the media URLs collected
                print(f"Media URLs collected: {media_urls}")

                self.total_files = len(media_urls)
                if media_urls:  # Solo proceder si hay URLs para descargar
                    futures = [self.executor.submit(self.download_file, url, folder, str(uuid.uuid4())) for url, folder in media_urls]
                    for future in as_completed(futures):
                        if self.cancel_requested:
                            self.log("Cancelling remaining downloads.")
                            break
                        future.result()

                self.log("Download initiated for all media.")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()
            else:
                self.log(f"Failed to access the post {url_post}: Status {response.status_code}")
        except Exception as e:
            self.log(f"Failed to access the post {url_post}: {e}")
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
                file_name_tag = soup.find('h1', {'class': 'text-[24px] font-bold text-dark dark:text-white'})
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

                        # Update progress for processing the profile
                        self.update_progress_callback(idx, total_links, file_id=None, file_path=None)

                        image_page_url = link['href']
                        self.log(f"Processing media page URL: {image_page_url}")

                        # Visit the page to get the media URL
                        image_response = self.session.get(image_page_url, headers=self.headers)
                        if image_response.status_code == 200:
                            image_soup = BeautifulSoup(image_response.text, 'html.parser')

                            # Search for image URL
                            media_tag = image_soup.select_one("figure.relative img[class='w-full h-full absolute opacity-20 object-cover blur-sm z-10']")
                            if media_tag and 'src' in media_tag.attrs:
                                media_url = media_tag['src']
                                self.log(f"Found image URL: {media_url}")
                                media_urls.append((media_url, ruta_carpeta))

                            # Search for video URL
                            video_tag = image_soup.select_one("video#player")
                            if video_tag and 'src' in video_tag.attrs:
                                video_url = video_tag['src']
                                self.log(f"Found video URL: {video_url}")
                                media_urls.append((video_url, ruta_carpeta))
                            else:
                                source_tag = video_tag.find('source') if video_tag else None
                                if source_tag and 'src' in source_tag.attrs:
                                    video_url = source_tag['src']
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
