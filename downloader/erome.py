import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

class EromeDownloader:
    def __init__(self, headers, translations, log_callback=None):
        self.headers = headers
        self.translations = translations
        self.log_callback = log_callback
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
        """Crea una carpeta si no existe."""
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        return folder_name
    
    def download_file(self, url, file_path, resource_type):
        if self.cancel_requested:  # Verificar si se ha solicitado cancelar antes de empezar la descarga
            return
        response = requests.get(url, headers=self.headers, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if self.cancel_requested:  # Verificar la cancelación durante la descarga
                        return
                    f.write(chunk)
            self.log("download_success", resource_type=resource_type, file_path=file_path)
        else:
            self.log("download_error", resource_type=resource_type, status_code=response.status_code)


    def process_album_page(self, page_url, base_folder):
        """Procesa una página de álbum individual y descarga los recursos."""
        if self.cancel_requested:  # Verificar si se ha solicitado cancelar antes de empezar la descarga
            return
        response = requests.get(page_url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Intenta obtener el título del álbum de la página
            folder_name = soup.find('h1').text if soup.find('h1') else "Album Desconocido"
            folder_path = self.create_folder(os.path.join(base_folder, self.clean_filename(folder_name)))
            
            # Descarga videos
            videos = soup.find_all('video')
            for video in videos:
                for source in video.find_all('source'):
                    video_src = source.get('src')
                    abs_video_src = urljoin(page_url, video_src)
                    video_name = os.path.join(folder_path, self.clean_filename(os.path.basename(abs_video_src)))
                    self.download_file(abs_video_src, video_name, 'Video')
            
            # Descarga imágenes dentro de 'div.img'
            image_divs = soup.select('div.img')
            for div in image_divs:
                img = div.find('img', attrs={'data-src': True})
                if img:
                    img_src = img.get('data-src')
                    abs_img_src = urljoin(page_url, img_src)
                    img_name = os.path.join(folder_path, self.clean_filename(os.path.basename(abs_img_src)))
                    self.download_file(abs_img_src, img_name, 'Imagen')
        else:
            self.log(f"Error al acceder a la página {page_url}. Código de estado: {response.status_code}")

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
