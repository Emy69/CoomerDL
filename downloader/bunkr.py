import os
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

class BunkrDownloader:
    def __init__(self, download_folder, log_callback=None, headers=None):
        self.download_folder = download_folder
        self.log_callback = log_callback
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            
        }
        self.cancel_requested = False
        
    def log(self, message):
        if self.log_callback is not None:
            self.log_callback(message)
    
    def request_cancel(self):
        self.cancel_requested = True   
        self.log("La descarga ha sido cancelada.") 
    
    def obtener_nombre_video(self, url_pagina):
        try:
            respuesta = requests.get(url_pagina, headers=self.headers)
            respuesta.raise_for_status()
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            h1_contenido = soup.find("h1", class_="text-[20px] font-bold text-dark dark:text-white").text.strip()
            return h1_contenido
        except Exception as e:
            self.log(f"Error al obtener el nombre del video desde {url_pagina}: {e}")
            return None

    def descargar_archivo(self, url_media, ruta_carpeta):
        if self.cancel_requested:
            self.log("Descarga cancelada por el usuario.")
            return  

        max_intentos = 3
        for intento in range(max_intentos):
            try:
                respuesta_media = requests.get(url_media, headers=self.headers)
                respuesta_media.raise_for_status()
                nombre_archivo = url_media.split('/')[-1]
                ruta_archivo = os.path.join(ruta_carpeta, nombre_archivo)
                
                with open(ruta_archivo, 'wb') as archivo:
                    for chunk in respuesta_media.iter_content(chunk_size=1024):
                        if self.cancel_requested:
                            self.log("Descarga cancelada durante la descarga del archivo.")
                            archivo.close()
                            os.remove(ruta_archivo)  
                            return
                        archivo.write(chunk)
                self.log(f"Archivo descargado: {nombre_archivo}")
                break
            except requests.RequestException as e:
                self.log(f"Error al descargar desde {url_media}: {e}. Intento {intento + 1} de {max_intentos}")
                if intento < max_intentos - 1:
                    time.sleep(3)



    def descargar_perfil_bunkr(self, url_perfil, download_images=True, download_videos=True):
        try:
            respuesta = self.session.get(url_perfil, headers=self.headers)
            if respuesta.status_code == 200:
                soup = BeautifulSoup(respuesta.text, 'html.parser')
                nombre_perfil = soup.find("h1", class_="text-[24px] font-bold text-dark dark:text-white").text.strip()
                ruta_carpeta = os.path.join(self.download_folder, nombre_perfil)
                os.makedirs(ruta_carpeta, exist_ok=True)
                
                enlaces = soup.find_all("a", class_="grid-images_box-link")
                for enlace in enlaces:
                    if self.cancel_requested:
                        self.log("Descarga cancelada por el usuario.")
                        break
                    href = enlace["href"]
                    if href.endswith(".mp4") or "/i/" in href:
                        if "/i/" in href:
                            parte_unico = href.split("/i/")[1]
                            url_media = f"https://i-burger.bunkr.ru/{parte_unico}"
                        else:
                            nombre_video = self.obtener_nombre_video(href)
                            if nombre_video:
                                url_media = f"https://burger.bunkr.ru/{nombre_video}"
        
                        self.descargar_archivo(url_media, ruta_carpeta)
                        
                        if self.cancel_requested:
                            break
            else:
                self.log(f"Error al acceder al perfil {url_perfil}: Estado {respuesta.status_code}")
        except Exception as e:
            self.log(f"Error al acceder al perfil {url_perfil}: {e}")
