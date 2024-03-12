# Importación de librerías necesarias
import requests
from bs4 import BeautifulSoup
import os
import threading
import tkinter as tk 
import customtkinter as ctk
from tkinter import filedialog
from urllib.parse import urljoin

# Definición de la clase principal de la aplicación
class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.download_requested = False  # Indica si se ha solicitado la descarga
        self.cancel_requested = False    # Indica si se ha solicitado la cancelación

        self.title("Image Downloader")
        self.geometry("800x490")

        # Creación de los widgets
        self.url_label = ctk.CTkLabel(self, text="URL de la página web:")
        self.url_label.pack(pady=(20, 0))

        self.url_entry = ctk.CTkEntry(self, width=400)
        self.url_entry.pack(pady=(10, 20))

        self.browse_button = ctk.CTkButton(self, text="Seleccionar Carpeta", command=self.select_folder)
        self.browse_button.pack()

        self.folder_path = ctk.CTkLabel(self, text="")
        self.folder_path.pack(pady=(10, 20))

        # Agregar un CTkTextbox para el log
        self.log_textbox = ctk.CTkTextbox(self, width=590, height=200, state='disabled')
        self.log_textbox.pack(pady=(10, 0))

        self.download_button = ctk.CTkButton(self, text="Descargar Imágenes", command=self.start_download_wrapper)
        self.download_button.pack()

        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_label.pack(pady=(20, 0))
        
    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        self.folder_path.configure(text=folder_selected)
        self.download_folder = folder_selected

    def start_download_wrapper(self):
        # Verificación y preparación para la descarga.
        if not hasattr(self, 'download_folder') or not self.url_entry.get():
            self.progress_label.configure(text="Seleccione una carpeta y una URL válida.")
            return

        self.disable_widgets()  # Deshabilita widgets al inicio de la descarga.
        self.progress_label.configure(text="Preparando descarga...")
        thread = threading.Thread(target=self.start_download)
        thread.start()

    def disable_widgets(self):
        # Deshabilita los widgets para evitar interacción durante la descarga.
        self.browse_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")

    def enable_widgets(self):
        # Habilita los widgets una vez finalizada la descarga.
        self.browse_button.configure(state="normal")
        self.download_button.configure(state="normal")
        self.url_entry.configure(state="normal")

    def add_log_message(self, message, message_type="info"):
        # Ejemplo de cómo podrías cambiar el color de fondo del CTkTextbox basado en el tipo de mensaje
        # Nota: Esta es una implementación ilustrativa; customtkinter no soporta cambiar el color del fondo de CTkTextbox después de su creación.
        if message_type == "info":
            color = "#D3D3D3"  # Light Gray para mensajes informativos
        elif message_type == "success":
            color = "#90EE90"  # Light Green para éxito
        elif message_type == "error":
            color = "#FFCCCB"  # Light Red para errores
        else:
            color = "#D3D3D3"  # Default a Light Gray
        message = f"{message}\n        ↳ Completo 100%"
        self.log_textbox.configure(state='normal')  # Habilitar escritura
        self.log_textbox.insert('end', message + '\n')  # Agregar mensaje
        self.log_textbox.configure(state='disabled', bg_color=color)  # Deshabilitar edición, intento de cambiar color
        self.log_textbox.yview_moveto(1)  # Auto-scroll


    def start_download(self):
        if not hasattr(self, 'download_folder') or not self.url_entry.get():
            self.progress_label.configure(text="Seleccione una carpeta y una URL válida.")
            return

        self.progress_label.configure(text="Preparando descarga...")
        url = self.url_entry.get()  # Obtén la URL de la entrada del usuario.
        image_urls = self.generate_image_links(url)  # Genera las URLs específicas de las imágenes.
        thread = threading.Thread(target=self.download_images, args=(image_urls,))  # Asegúrate de pasar image_urls como argumento.
        thread.start()

    def generate_image_links(self, start_url):
        image_urls = []
        try:
            response = requests.get(start_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.find_all('article', class_='post-card post-card--preview')

            for post in posts:
                data_id = post.get('data-id')
                data_service = post.get('data-service')
                data_user = post.get('data-user')

                if data_id and data_service and data_user:
                    image_url = f"https://coomer.su/{data_service}/user/{data_user}/post/{data_id}"
                    image_urls.append(image_url)

        except Exception as e:
            self.add_log_message(f"Error durante la recopilación de links: {str(e)}")
        
        return image_urls

    def download_images(self, image_urls):
        try:
            if not image_urls:  # Si no hay URLs para procesar, actualiza el log directamente.
                self.add_log_message("No se encontraron URLs para descargar.")
                return

            for i, page_url in enumerate(image_urls):
                page_response = requests.get(page_url)
                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                
                # Procesa imágenes
                image_elements = page_soup.select('div.post__thumbnail img')
                for idx, image_element in enumerate(image_elements):
                    self.process_media_element(image_element, i, idx, page_url, "imagen")

                # Procesa videos
                video_elements = page_soup.select('ul.post__attachments li.post__attachment a.post__attachment-link')
                for idx, video_element in enumerate(video_elements):
                    self.process_media_element(video_element, i, idx, page_url, "video")

                if not image_elements and not video_elements:
                    self.add_log_message(f"No se encontraron medios en URL: {page_url}")

            self.add_log_message("Descarga Terminada.")
        except Exception as e:
            self.add_log_message(f"Error durante la descarga: {str(e)}")
        finally:
            self.enable_widgets()  

    def process_media_element(self, element, page_idx, media_idx, page_url, media_type):
        media_url = element.get('src') or element.get('data-src') or element.get('href')
        if media_url.startswith('//'):
            media_url = "https:" + media_url
        elif not media_url.startswith('http'):
            media_url = urljoin("https://coomer.su/", media_url)
        media_data = requests.get(media_url).content
        extension = media_url.split('.')[-1].split('?')[0]
        filename = f"{media_type}_{page_idx}_{media_idx}.{extension}"
        filepath = os.path.join(self.download_folder, filename)
        with open(filepath, 'wb') as file:
            file.write(media_data)
        #self.add_log_message(f"Descargado {media_type} {page_idx+1}-{media_idx+1}")
        self.add_log_message(f"Descargado {media_type} {page_idx+1}-{media_idx+1} de URL: {page_url}")

if __name__ == "__main__":
    app = ImageDownloaderApp()
    app.mainloop()