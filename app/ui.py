import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from downloader.downloader import Downloader  # Ajusta esta línea según tu estructura de importación real
import threading

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Inicialización
        self.downloader = None  # Se establecerá correctamente después

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

    def setup_downloader(self):
        self.downloader = Downloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message  # La referencia al callback para logs
        )

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:  
            self.folder_path.configure(text=folder_selected)
            self.download_folder = folder_selected
            # Configura el objeto downloader aquí y pasa las referencias necesarias
            self.setup_downloader()


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

    def start_download_wrapper(self):
        if not self.download_folder or not self.url_entry.get():
            self.progress_label.configure(text="Seleccione una carpeta y una URL válida.")
            return
        self.disable_widgets()  # Deshabilita widgets al inicio de la descarga.
        self.progress_label.configure(text="Preparando descarga...")
        # Ahora, usa threading aquí para empezar la descarga sin bloquear la UI
        threading.Thread(target=self.start_download).start()


    def start_download(self):
        url = self.url_entry.get()
        # Usa el objeto downloader directamente aquí para la descarga
        image_urls = self.downloader.generate_image_links(url)
        self.downloader.download_images(image_urls)  # Asume que maneja una lista de URLs

        # Tras finalizar la descarga, vuelve a habilitar los widgets
        # Esto debe hacerse de manera segura ya que estamos en un hilo diferente
        self.after(0, self.enable_widgets)


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