from tkinter import messagebox, simpledialog
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import json

class EromeDownloader:
    def __init__(self, root, log_callback=None,enable_widgets_callback=None, download_images=True, download_videos=True, headers=None, language="en"):
        self.root = root
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.download_images = download_images
        self.download_videos = download_videos
        self.cancel_requested = False
        self.language = language
        self.translations = self.load_translations(language)
    
    def load_translations(self, language):
        try:
            with open(f"resources/config/languages/{language}.json", "r") as file:
                translations = json.load(file)
            return translations
        except FileNotFoundError:
            print(f"Translation file for '{language}' not found. Falling back to English.")
            with open("resources/config/languages/en.json", "r") as file:
                return json.load(file)

    def tr(self, key):
        return self.translations.get(key, f"[{key} not translated]")

    # Método para solicitar la cancelación del proceso de descarga
    def request_cancel(self):
        self.cancel_requested = True
        self.log(self.tr("cancel_download"))
        self.enable_widgets_callback()

    def log(self, message):
        if self.log_callback is not None:
            self.log_callback(message)

    @staticmethod
    def clean_filename(filename):
        return filename.split('?')[0]

    def create_folder(self, folder_name):
        try:
            os.makedirs(folder_name, exist_ok=True)
        except OSError as e:
            self.log(self.tr("create_folder_error").format(error=e))
            response = messagebox.askyesno(self.tr("choose_new_folder_name").format(folder_name=folder_name), parent=self.root)
            if response:
                new_folder_name = simpledialog.askstring(self.tr("new_folder_name"), parent=self.root)
                if new_folder_name:
                    folder_name = os.path.join(os.path.dirname(folder_name), new_folder_name)
                    try:
                        os.makedirs(folder_name, exist_ok=True)
                    except OSError as e:
                        messagebox.showerror(self.tr("folder_creation_failed").format(folder_name=folder_name, error=e), parent=self.root)
        return folder_name

    
    def download_file(self, url, file_path, resource_type):
        if self.cancel_requested:
            return

        # Ensure the folder where the file will be saved exists
        folder_path = os.path.dirname(file_path)
        os.makedirs(folder_path, exist_ok=True)

        if resource_type == "Video":
            self.log(self.tr("start_download_video").format(file_path=file_path))

        # Start the download request with streaming
        response = requests.get(url, headers=self.headers, stream=True)

        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if self.cancel_requested:
                        return
                    f.write(chunk)

            self.log(self.tr("download_successful").format(resource_type=resource_type, file_path=file_path))
        else:
            self.log(self.tr("download_error").format(resource_type=resource_type, status_code=response.status_code))


    def process_album_page(self, page_url, base_folder, download_images=True, download_videos=True):
        try:
            if self.cancel_requested:
                return
            response = requests.get(page_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Obtener y limpiar el nombre del álbum para usarlo como nombre de carpeta
                folder_name = self.clean_filename(soup.find('h1').text if soup.find('h1') else "Album Desconocido")
                folder_path = self.create_folder(os.path.join(base_folder, folder_name))
                
                # Descarga videos
                if self.download_videos:
                    video_urls = set()  # Conjunto para almacenar y verificar duplicados
                    videos = soup.find_all('video')
                    for video in videos:
                        source = video.find('source')
                        if source:
                            video_src = source['src']
                            if video_src not in video_urls:  # Verificar duplicados
                                video_urls.add(video_src)
                                abs_video_src = urljoin(page_url, video_src)
                                video_name = os.path.join(folder_path, self.clean_filename(os.path.basename(abs_video_src)))
                                self.download_file(abs_video_src, video_name, 'Video')

                # Descarga imágenes
                if self.download_images:
                    image_divs = soup.select('div.img')
                    for div in image_divs:
                        img = div.find('img', attrs={'data-src': True})
                        if img:
                            img_src = img['data-src']
                            abs_img_src = urljoin(page_url, img_src)
                            img_name = os.path.join(folder_path, self.clean_filename(os.path.basename(abs_img_src)))
                            self.download_file(abs_img_src, img_name, 'Imagen')
                
                self.log(self.tr("album_download_complete").format(album_name=folder_name))
            else:
                self.log(f"Error al acceder a la página {page_url}. Código de estado: {response.status_code}")
                if self.enable_widgets_callback:
                    self.enable_widgets_callback()  
        finally:
            if self.enable_widgets_callback:
                self.enable_widgets_callback()  


    def process_profile_page(self, url, download_folder, download_images, download_videos):
        try:
            """Procesa una página de perfil, encontrando y procesando cada álbum listado."""
            if self.cancel_requested:  
                return
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                username = soup.find('h1', class_='username').text.strip() if soup.find('h1', class_='username') else "Perfil Desconocido"
                base_folder = self.create_folder(self.clean_filename(username))
                
                
                album_links = soup.find_all('a', class_='album-link')
                for album_link in album_links:
                    album_href = album_link.get('href')
                    album_full_url = urljoin(url, album_href)
                    self.process_album_page(album_full_url, base_folder)
                    
                self.log(self.tr("profile_download_complete").format(profile_name=username))
            else:
                self.log(f"Error al acceder al perfil {url}. Código de estado: {response.status_code}")
        finally:
            if self.enable_widgets_callback:
                self.enable_widgets_callback()  