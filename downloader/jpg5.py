import requests
from bs4 import BeautifulSoup
import os
import threading
from concurrent.futures import ThreadPoolExecutor

class Jpg5Downloader:
    def __init__(self, url, carpeta_destino, progress_manager, log_callback=None, tr=None, update_progress_callback=None, update_global_progress_callback=None, max_workers=3):
        self.url = url
        self.carpeta_destino = carpeta_destino
        self.log_callback = log_callback
        self.tr = tr if tr else lambda x: x  # Función de traducción por defecto
        self.cancel_requested = threading.Event()  # Usar un evento para manejar la cancelación
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.max_workers = max_workers
        self.progress_manager = progress_manager

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def request_cancel(self):
        self.cancel_requested.set()  # Activar el evento de cancelación
        self.log(self.tr("Descarga cancelada por el usuario."))

    def descargar_imagenes(self):
        if not os.path.exists(self.carpeta_destino):
            os.makedirs(self.carpeta_destino)

        self.log(self.tr(f"Iniciando descarga desde: {self.url}"))
        respuesta = requests.get(self.url)
        if self.cancel_requested.is_set():
            self.log(self.tr("Descarga cancelada por el usuario."))
            return

        soup = BeautifulSoup(respuesta.content, 'html.parser')

        divs = soup.find_all('div', class_='list-item c8 gutter-margin-right-bottom')
        total_divs = len(divs)
        self.log(self.tr(f"Total de elementos a procesar: {total_divs}"))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for i, div in enumerate(divs):
                if self.cancel_requested.is_set():
                    self.log(self.tr("Descarga cancelada por el usuario."))
                    return

                enlaces = div.find_all('a', class_='image-container --media')
                for enlace in enlaces:
                    if self.cancel_requested.is_set():
                        self.log(self.tr("Descarga cancelada por el usuario."))
                        return

                    futures.append(executor.submit(self.descargar_enlace, enlace, i, total_divs))

            for future in futures:
                future.result()  # Esperar a que todas las descargas terminen

    def descargar_enlace(self, enlace, i, total_divs):
        try:
            media_url = enlace['href']
            self.log(self.tr(f"Procesando enlace: {media_url}"))

            media_respuesta = requests.get(media_url)
            if self.cancel_requested.is_set():
                self.log(self.tr("Descarga cancelada por el usuario."))
                return

            media_soup = BeautifulSoup(media_respuesta.content, 'html.parser')

            header_content = media_soup.find('div', class_='header-content-right')
            if header_content:
                btn_descarga = header_content.find('a', class_='btn btn-download default')
                if btn_descarga and 'href' in btn_descarga.attrs:
                    descarga_url = btn_descarga['href']
                    self.log(self.tr(f"Descargando desde: {descarga_url}"))

                    img_respuesta = requests.get(descarga_url, stream=True)
                    if self.cancel_requested.is_set():
                        self.log(self.tr("Descarga cancelada por el usuario."))
                        return

                    img_nombre = os.path.basename(descarga_url)
                    img_path = os.path.join(self.carpeta_destino, img_nombre)
                    total_size = int(img_respuesta.headers.get('content-length', 0))
                    downloaded_size = 0

                    with open(img_path, 'wb') as f:
                        for chunk in img_respuesta.iter_content(chunk_size=1024):
                            if self.cancel_requested.is_set():
                                self.log(self.tr("Descarga cancelada por el usuario."))
                                return
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if self.update_progress_callback:
                                self.update_progress_callback(downloaded_size, total_size)

                    self.log(self.tr(f"Imagen descargada: {img_nombre}"))

                    if self.update_global_progress_callback:
                        self.update_global_progress_callback(i + 1, total_divs)
                else:
                    self.log(self.tr("No se encontró el enlace de descarga."))
            else:
                self.log(self.tr("No se encontró la clase 'header-content-right'."))
        except Exception as e:
            self.log(self.tr(f"Error al procesar el enlace: {e}"))