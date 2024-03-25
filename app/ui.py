import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from downloader.downloader import Downloader  
import threading, os,json

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Coomer Downloader [Beta-V0.3]")
        self.geometry("800x600")
        self.download_folder = None
        self.iconbitmap("resources/img/window.ico")
        self.load_translations()
        self.current_language = "spanish"
        self.load_language_preference()  
        self.initialize_ui()
        self.apply_translations()

    def initialize_ui(self):
        # Frame para la URL y selección de carpeta
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=20, fill='x', padx=20)

        # Crear un menú principal para la ventana
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

       # Agregar un menú de configuración
        self.settings_menu_label = "Configuración"  # Initial label, will be updated
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=self.settings_menu_label, menu=self.settings_menu)

        # Store a reference to the 'Change Language' menu item
        self.change_language_menu_item = self.settings_menu.add_command(label="Cambiar Idioma", command=self.open_language_settings)

        self.url_label = ctk.CTkLabel(self.input_frame, text="URL de la página web:")
        self.url_label.grid(row=1, column=0, sticky='w')

        self.url_entry = ctk.CTkEntry(self.input_frame, width=300)
        self.url_entry.grid(row=2, column=0, sticky='we', padx=(0, 5))


        self.browse_button = ctk.CTkButton(self.input_frame, text="Seleccionar Carpeta", command=self.select_folder)
        self.browse_button.grid(row=2, column=1, sticky='e')


        self.input_frame.columnconfigure(0, weight=1)  # Hace que la columna 0 (entrada de URL) se expanda para llenar el espacio extra

        self.folder_path = ctk.CTkLabel(self.input_frame, text="")
        self.folder_path.grid(row=3, column=0, columnspan=2, sticky='w')

        # Frame para opciones de descarga
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, fill='x', padx=20)

        self.download_images_check = ctk.CTkCheckBox(self.options_frame, text="Descargar Imágenes", onvalue=True, offvalue=False)
        self.download_images_check.pack(side='left', padx=10)
        self.download_images_check.select()

        self.download_videos_check = ctk.CTkCheckBox(self.options_frame, text="Descargar Vídeos", onvalue=True, offvalue=False)
        self.download_videos_check.pack(side='left', padx=10)
        self.download_videos_check.select()

        # Frame para botones de acción y estado de descarga
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.pack(pady=10, fill='x', padx=20)

        self.download_speed_label = ctk.CTkLabel(self.action_frame, text="Velocidad de descarga: 0 KB/s")
        self.download_speed_label.pack(side='left', padx=10)

        self.download_button = ctk.CTkButton(self.action_frame, text="Descargar", command=self.start_download_wrapper)
        self.download_button.pack(side='left', padx=10)

        self.cancel_button = ctk.CTkButton(self.action_frame, text="Cancelar Descarga", command=self.request_cancel, state="disabled")
        self.cancel_button.pack(side='left', padx=10)

        self.progress_label = ctk.CTkLabel(self.action_frame, text="")
        self.progress_label.pack(side='left', padx=10)

        # Log de actividad
        self.log_textbox = ctk.CTkTextbox(self, width=590, height=200, state='disabled')
        self.log_textbox.pack(pady=(10, 0), padx=20, fill='both', expand=True)

    def load_translations(self):
        current_dir = os.path.dirname(__file__)
        path_to_file = os.path.join(current_dir, '../resources/languages.json')
        
        with open(path_to_file, 'r', encoding='utf-8') as f:
            self.translations = json.load(f)

    def apply_translations(self):
        t = self.translations[self.current_language]
        
        # Actualiza el título de la ventana y otros elementos UI directamente.
        self.title(t["window_title"])
        self.url_label.configure(text=t["webpage_url"])
        self.browse_button.configure(text=t["select_folder"])
        self.download_images_check.configure(text=t["download_images"])
        self.download_videos_check.configure(text=t["download_videos"])
        self.download_button.configure(text=t["download"])
        self.cancel_button.configure(text=t["cancel_download"])
        
        # Actualiza las etiquetas del menú y submenús directamente.
        self.build_menus(t)

    def build_menus(self, translations):
        self.menu_bar.delete(0, 'end')
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=translations["settings_menu"], menu=self.settings_menu)
        self.settings_menu.add_command(label=translations["change_language"], command=self.open_language_settings)

    def setup_downloader(self):
        # Asegúrate de llamar a este método después de cargar las traducciones y cuando cambies el idioma.
        self.downloader = Downloader(
            download_folder=self.download_folder,
            translations=self.translations[self.current_language],  # Traducciones basadas en el idioma actual
            log_callback=self.add_log_message,
            enable_widgets_callback=self.enable_widgets,
            update_speed_callback=self.update_download_speed
        )
    
    def toggle_language(self):
        # Cambiar el idioma actual
        self.current_language = "english" if self.current_language == "spanish" else "spanish"
        
        # Aplicar las traducciones al UI basado en el nuevo idioma
        self.apply_translations()
        
        # Actualizar las traducciones usadas en Downloader
        self.setup_downloader()

    def update_download_speed(self, speed):
        # Obtiene la traducción para 'download_speed'
        speed_template = self.translations[self.current_language]["download_speed"]
        # Formatea la cadena con el valor de velocidad actual
        speed_text = speed_template.format(speed=speed)
        # Actualiza el texto de 'download_speed_label' en el hilo principal de Tkinter
        self.after(0, lambda: self.download_speed_label.configure(text=speed_text))

    def open_language_settings(self):
        t = self.translations[self.current_language]

        # Esta función abre un diálogo simple con opciones de idioma
        language_window = ctk.CTkToplevel(self)
        language_window.title(t["select_language"])

        # Calcula la posición central basada en la ventana principal
        window_width = 200
        window_height = 100
        position_right = int(self.winfo_screenwidth()/2 - window_width/2)
        position_down = int(self.winfo_screenheight()/2 - window_height/2)

        # Configura el tamaño y posición de la ventana
        language_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")

        # Si CustomTkinter es compatible con Toplevel, usa ctk.CTkButton aquí
        ctk.CTkButton(language_window, text="English", command=lambda: self.set_language("english")).pack(fill='x', padx=20, pady=5)
        ctk.CTkButton(language_window, text="Español", command=lambda: self.set_language("spanish")).pack(fill='x', padx=20, pady=5)

        # Hace que la ventana de configuración de idioma sea modal
        language_window.transient(self)
        language_window.grab_set()
        self.wait_window(language_window)


    def set_language(self, language):
        self.current_language = language
        self.apply_translations()
        self.save_language_preference()
    
    def save_language_preference(self):
        with open("resources/config/config.json", "w") as config_file:
            json.dump({"language": self.current_language}, config_file)

    def load_language_preference(self):
        try:
            with open("resources/config/config.json", "r") as config_file:
                config = json.load(config_file)
                self.current_language = config.get("language", "spanish")
        except FileNotFoundError:
            self.current_language = "spanish"

    def request_cancel(self):
        if self.downloader:
            self.downloader.request_cancel()

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:  
            self.folder_path.configure(text=folder_selected)
            self.download_folder = folder_selected  
            self.setup_downloader()

    def add_log_message(self, message):
        message = f"{message}\n"
        self.log_textbox.configure(state='normal')  # Habilitar escritura
        self.log_textbox.insert('end', message + '\n')  # Agregar mensaje
        self.log_textbox.configure(state='disabled')
        self.log_textbox.yview_moveto(1)  # Auto-scroll

    def start_download_wrapper(self):
        if not self.download_folder or not self.url_entry.get():
            translation = self.translations[self.current_language]["select_folder_url_valid"]
            self.progress_label.configure(text=translation)
            return
        self.disable_widgets()  # Deshabilita widgets al inicio de la descarga.
        self.cancel_button.configure(state="normal")
        translation = self.translations[self.current_language]["preparing_download"]
        self.progress_label.configure(text=translation)
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
            self.add_log_message("No se pudo obtener el nombre de la página, usando carpeta predeterminada.")

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