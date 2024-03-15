import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from downloader.downloader import Downloader  # Ajusta esta línea según tu estructura de importación real
import threading, os

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Inicialización
        self.downloader = None  
        self.download_folder = None
        
        self.title("Coomer Downloader [Beta-V0.3]")
        self.geometry("800x600")

        # Creación de los widgets
        self.url_label = ctk.CTkLabel(self, text="URL de la página web:")
        self.url_label.pack(pady=(20, 0))

        self.url_entry = ctk.CTkEntry(self, width=400)
        self.url_entry.pack(pady=(10, 20))

        self.browse_button = ctk.CTkButton(self, text="Seleccionar Carpeta", command=self.select_folder)
        self.browse_button.pack()

        self.folder_path = ctk.CTkLabel(self, text="")
        self.folder_path.pack(pady=(10, 20))

        # Casilla de verificación para descargar imágenes
        self.download_images_check = ctk.CTkCheckBox(self, text="Descargar Imágenes", onvalue=True, offvalue=False)
        self.download_images_check.pack(pady=(10, 0))
        self.download_images_check.select()  # Seleccionado por defecto

        # Casilla de verificación para descargar videos
        self.download_videos_check = ctk.CTkCheckBox(self, text="Descargar Vídeos", onvalue=True, offvalue=False)
        self.download_videos_check.pack(pady=(10, 20))
        self.download_videos_check.select()  # Seleccionado por defecto

        # Agregar un CTkTextbox para el log
        self.log_textbox = ctk.CTkTextbox(self, width=590, height=200, state='disabled')
        self.log_textbox.pack(pady=(10, 0))

        self.download_button = ctk.CTkButton(self, text="Descargar Imágenes", command=self.start_download_wrapper)
        self.download_button.pack()

        self.cancel_button = ctk.CTkButton(self, text="Cancelar Descarga", command=self.request_cancel)
        self.cancel_button.pack()
        self.cancel_button.configure(state="disabled")  

        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_label.pack(pady=(20, 0))

    def setup_downloader(self):
        self.downloader = Downloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message,
            enable_widgets_callback=self.enable_widgets
        )

    def request_cancel(self):
        if self.downloader:
            self.downloader.request_cancel()

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:  
            self.folder_path.configure(text=folder_selected)
            self.download_folder = folder_selected  # Actualiza download_folder con la carpeta seleccionada
            # Configura el objeto downloader aquí y pasa las referencias necesarias
            self.setup_downloader()


    def add_log_message(self, message):
        message = f"{message}\n"
        self.log_textbox.configure(state='normal')  # Habilitar escritura
        self.log_textbox.insert('end', message + '\n')  # Agregar mensaje
        self.log_textbox.configure(state='disabled')  # Deshabilitar edición, intento de cambiar color
        self.log_textbox.yview_moveto(1)  # Auto-scroll

    def start_download_wrapper(self):
        if not self.download_folder or not self.url_entry.get():
            self.progress_label.configure(text="Seleccione una carpeta y una URL válida.")
            return
        self.disable_widgets()  # Deshabilita widgets al inicio de la descarga.
        self.cancel_button.configure(state="normal") 
        self.progress_label.configure(text="Preparando descarga...")
        # Ahora,threading aquí para empezar la descarga sin bloquear la UI
        threading.Thread(target=self.start_download).start()
        

    def start_download(self):
        url = self.url_entry.get()
        image_urls, folder_name = self.downloader.generate_image_links(url)  # Ahora devuelve también el nombre de la carpeta
        if folder_name:  # Verifica que el nombre de la carpeta no esté vacío
            # Crea el subdirectorio con el nombre de la carpeta
            specific_download_folder = os.path.join(self.download_folder, folder_name)
            os.makedirs(specific_download_folder, exist_ok=True)
            # Actualiza la carpeta de descarga en el objeto downloader
            self.downloader.download_folder = specific_download_folder
        else:
            # Maneja el caso de que no se haya podido obtener un nombre de carpeta
            self.log_callback("No se pudo obtener el nombre de la página, usando carpeta predeterminada.")

        download_images_pref = self.download_images_check.get()
        download_videos_pref = self.download_videos_check.get()
        self.downloader.download_images(image_urls, download_images_pref, download_videos_pref)



    def disable_widgets(self):
        # Deshabilita los widgets para evitar interacción durante la descarga.
        self.browse_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")

    def enable_widgets(self):
        # Habilita los widgets una vez finalizada la descarga.
        self.cancel_button.configure(state="disabled")  
        self.browse_button.configure(state="normal")
        self.download_button.configure(state="normal")
        self.url_entry.configure(state="normal")