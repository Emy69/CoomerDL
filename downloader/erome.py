from tkinter import messagebox, simpledialog
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

class EromeDownloader:
    def __init__(self,root, headers, translations, log_callback=None, download_images=True, download_videos=True):
        self.root = root
        self.headers = headers
        self.translations = translations
        self.log_callback = log_callback
        self.download_images = download_images
        self.download_videos = download_videos
        self.cancel_requested = False

    # Método para solicitar la cancelación del proceso de descarga
    def request_cancel(self):
        self.cancel_requested = True
        self.log("cancel_download")

    def log(self, message_key, **kwargs):
        if self.log_callback is not None:
            message = self.translations[message_key].format(**kwargs)
            self.log_callback(message)

    @staticmethod
    def clean_filename(filename):
        """Limpia el nombre del archivo eliminando o reemplazando caracteres no válidos."""
        return filename.split('?')[0]

    def create_folder(self, folder_name):
        """Intenta crear una carpeta, y si falla, pide al usuario que ingrese un nuevo nombre."""
        try:
            os.makedirs(folder_name, exist_ok=True)
        except OSError as e:
            self.log("error_creating_folder", error=str(e))
            response = messagebox.askyesno("Error", f"No se pudo crear la carpeta: {folder_name}\n¿Quieres elegir un nuevo nombre?", parent=self.root)
            if response:
                new_folder_name = simpledialog.askstring("Nuevo nombre", "Ingresa el nuevo nombre de la carpeta:", parent=self.root)
                if new_folder_name:
                    folder_name = os.path.join(os.path.dirname(folder_name), new_folder_name)
                    try:
                        os.makedirs(folder_name, exist_ok=True)
                    except OSError as e:
                        messagebox.showerror("Error", f"No se pudo crear la carpeta: {folder_name}\nError: {e}", parent=self.root)
        return folder_name

    
    def download_file(self, url, file_path, resource_type):
        if self.cancel_requested:  
            return
        
        # Asegura que la carpeta donde se guardará el archivo exista
        folder_path = os.path.dirname(file_path)
        os.makedirs(folder_path, exist_ok=True)  # Crea la carpeta si no existe
        
        if resource_type == "Video":
            self.log("start_video_download", file_path=file_path)
        
        # Inicia la petición de descarga con streaming para permitir la descarga en bloques
        response = requests.get(url, headers=self.headers, stream=True)
        
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                # Define un chunk_size de 65536 bytes (64KB)
                for chunk in response.iter_content(chunk_size=65536): 
                    if self.cancel_requested: 
                        return
                    f.write(chunk)
            
            self.log("download_success", resource_type=resource_type, file_path=file_path)
        else:
            self.log("download_error", resource_type=resource_type, status_code=response.status_code)


    def process_album_page(self, page_url, base_folder):
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
        else:
            self.log("error_accessing_page", page_url=page_url, status_code=response.status_code)

    def process_profile_page(self, profile_url):
        """Procesa una página de perfil, encontrando y procesando cada álbum listado."""
        if self.cancel_requested:  # Verificar si se ha solicitado cancelar antes de empezar la descarga
            return
        response = requests.get(profile_url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Obtén el nombre del perfil como nombre base de la carpeta
            username = soup.find('h1', class_='username').text.strip() if soup.find('h1', class_='username') else "Perfil Desconocido"
            base_folder = self.create_folder(self.clean_filename(username))
            
            # Encuentra y procesa cada álbum en el perfil
            album_links = soup.find_all('a', class_='album-link')
            for album_link in album_links:
                album_href = album_link.get('href')
                album_full_url = urljoin(profile_url, album_href)
                self.process_album_page(album_full_url, base_folder)
        else:
            self.log(f"Error al acceder al perfil {profile_url}. Código de estado: {response.status_code}")