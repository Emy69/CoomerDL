import tkinter as tk
from tkinter import Tk, messagebox
from tkinter import Menu
import webbrowser
import customtkinter as ctk
from tkinter import filedialog
from downloader.downloader import Downloader  
import threading, os,json,sys
from pathlib import Path
from downloader.erome import EromeDownloader
from app.settings import open_language_settings, show_about_dialog


class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title("Downloader [V0.4.1]")

        # Configura el tamaño de la ventana
        window_width = 1000
        window_height = 680

        # Obtiene las dimensiones de la pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calcula la posición x e y para centrar la ventana
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))

        # Establece la geometría de la ventana para centrarla
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        self.download_folder = None
        self.iconbitmap("resources/img/window.ico")
        self.load_translations()
        self.current_language = "spanish"
        self.load_language_preference()
        self.initialize_ui()
        self.apply_translations()
        self.erome_downloader = None
        self.is_downloading = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.closing = False

    def on_close(self):
        t = self.translations[self.current_language]
        if self.is_downloading:
            if messagebox.askokcancel(t["exit_title"], t["exit_confirmation"]):
                self.closing = True  # Indicates that the application is closing
                self.erome_downloader.request_cancel()  # Cancel the download
                self.destroy()
        else:
            self.closing = True  # Indicates that the application is closing
            self.destroy()

    def initialize_ui(self):
        # Frame para la URL y selección de carpeta
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=20, fill='x', padx=20)

        # Crear un menú principal para la ventana
        self.menu_bar = tk.Menu(self, bg="#333333", fg="white", bd=0, activebackground="#555555", activeforeground="white")
        self.config(menu=self.menu_bar)

        # Configurar el menú de configuración
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#333333", fg="white", bd=0, activebackground="#555555", activeforeground="white")
        self.menu_bar.add_cascade(label=self.translations[self.current_language]["settings_menu"], menu=self.settings_menu)
        self.settings_menu.add_command(label=self.translations[self.current_language]["change_language"], command=lambda: open_language_settings(self))

        # Configurar el menú de ayuda
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#333333", fg="white", bd=0, activebackground="#555555", activeforeground="white")
        self.menu_bar.add_cascade(label=self.translations[self.current_language]["help"], menu=self.help_menu)
        self.help_menu.add_command(label=self.translations[self.current_language]["about"], command=lambda: show_about_dialog(self))
        self.help_menu.add_command(label=self.translations[self.current_language]["help_and_feedback"], command=self.open_help_and_feedback)

        self.url_label = ctk.CTkLabel(self.input_frame, text="URL de la página web:")
        self.url_label.grid(row=1, column=0, sticky='w')

        self.url_entry = ctk.CTkTextbox(self.input_frame, width=300, height=80, wrap="none")
        self.url_entry.grid(row=2, column=0, sticky='we', padx=(0, 5))

        # Configura el menú de clic derecho para el cuadro de texto
        self.right_click_menu = Menu(self, tearoff=0)
        self.right_click_menu.add_command(label=self.translations[self.current_language]["paste"], command=self.paste_from_clipboard)

        # Configura el evento de clic derecho en el cuadro de texto
        self.url_entry.bind("<Button-3>", self.show_right_click_menu)

        self.browse_button = ctk.CTkButton(self.input_frame,width=30, height=80, text="Seleccionar Carpeta", command=self.select_folder)
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
    
    def paste_from_clipboard(self):
        try:
            # Obtiene texto del portapapeles y lo inserta en el cuadro de texto
            text_to_paste = self.clipboard_get()
            self.url_entry.insert('insert', text_to_paste)
        except Exception as e:
            print(f"Error pegando texto: {e}")

    def show_right_click_menu(self, event):
        try:
            # Muestra el menú de clic derecho en las coordenadas del evento
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Asegura que el menú de clic derecho se cierra correctamente
            self.right_click_menu.grab_release()

    def load_translations(self):
        # Verificar si se está ejecutando como un ejecutable congelado
        if getattr(sys, 'frozen', False):
            # Si es así, usar la ruta relativa al ejecutable
            application_path = Path(sys.executable).parent
        else:
            # Si no, usar la ruta relativa al script
            application_path = Path(__file__).parent.parent

        path_to_file = application_path / 'resources' / 'languages.json'

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
        self.build_menus()

    def build_menus(self):
        t = self.translations[self.current_language]

        # Limpiar menús existentes
        self.menu_bar.delete(0, 'end')

        # Configurar el menú de Configuración
        settings_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#333333", fg="white", bd=0, activebackground="#555555", activeforeground="white")
        self.menu_bar.add_cascade(label=t["settings_menu"], menu=settings_menu)
        settings_menu.add_command(label=t["change_language"], command=lambda: open_language_settings(self))

        # Configurar el menú de Ayuda
        help_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#333333", fg="white", bd=0, activebackground="#555555", activeforeground="white")
        self.menu_bar.add_cascade(label=t["help"], menu=help_menu)
        help_menu.add_command(label=t["about"], command=lambda: show_about_dialog(self))
        help_menu.add_command(label=t["help_and_feedback"], command=self.open_help_and_feedback)

        # Aplicar el menú a la ventana principal
        self.config(menu=self.menu_bar)

        
    def open_help_and_feedback(self):
        webbrowser.open("https://github.com/Emy69/CoomerDL/issues")

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
        t = self.translations[self.current_language]
        if self.downloader:
            self.downloader.request_cancel()
        if hasattr(self, 'erome_downloader'):
            self.erome_downloader.request_cancel()
            self.add_log_message(t["cancel_user"])


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
        current_language = self.current_language  # Asegúrate de tener esta propiedad en tu instancia de aplicación
        translations = self.translations[current_language]

        # Obtiene el estado de las preferencias de descarga
        download_images_pref = self.download_images_check.get()
        download_videos_pref = self.download_videos_check.get()

        # Verifica si no se ha seleccionado al menos una opción
        if not download_images_pref and not download_videos_pref:
            messagebox.showwarning(translations["warning_title"], translations["download_option_warning"])
            return

        urls = self.url_entry.get("1.0", "end-1c").splitlines()
        urls = [url for url in urls if url.strip()]
        if len(urls) > 5:
            messagebox.showinfo(translations["limitation_title"], translations["url_limit_warning"])
            return
        if not self.download_folder or not urls:
            translation = self.translations[self.current_language]["select_folder_url_valid"]
            self.progress_label.configure(text=translation)
            return
        self.disable_widgets()
        self.downloader.cancel_requested = False
        self.cancel_button.configure(state="normal")
        translation = self.translations[self.current_language]["preparing_download"]
        self.progress_label.configure(text=translation)
        self.is_downloading = True
        download_thread = threading.Thread(target=self.start_download, args=(urls,))
        download_thread.start()


    def start_download(self, urls):
        # Obtiene las preferencias de descarga directamente de los checkboxes en la UI.
        download_images_pref = self.download_images_check.get()
        download_videos_pref = self.download_videos_check.get()

        try:
            # Inicializa la instancia de EromeDownloader con las preferencias de descarga
            root = Tk()
            self.erome_downloader = EromeDownloader(root,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                    'Referer': 'https://www.erome.com/'
                },
                translations=self.translations[self.current_language],
                log_callback=self.add_log_message,
                download_images=download_images_pref,
                download_videos=download_videos_pref,
                
                
            )
        
            for index, url in enumerate(urls):
                t = self.translations[self.current_language]
                if self.downloader.cancel_requested or self.closing:
                    # Registra o maneja la cancelación aquí si es necesario
                    self.add_log_message("cancel_user")
                    break  # Salir del ciclo for si se solicitó la cancelación

                if len(url.strip()) == 0:  # Omitir líneas vacías
                    continue

                if "/a/" in url:
                    self.erome_downloader.process_album_page(url, self.download_folder)
                else:
                    self.erome_downloader.process_profile_page(url)

                # Actualiza el log y la UI conforme sea necesario
                self.add_log_message(t["download_completed_from"])

                self.progress_label.configure(text=f"Descargando de {url}...")
                image_urls, folder_name = self.downloader.generate_image_links(url)
                if folder_name:
                    specific_download_folder = os.path.join(self.download_folder, folder_name)
                    os.makedirs(specific_download_folder, exist_ok=True)
                    self.downloader.download_folder = specific_download_folder
                else:
                    self.add_log_message("No se pudo obtener el nombre de la página, usando carpeta predeterminada.")
                download_images_pref = self.download_images_check.get()
                download_videos_pref = self.download_videos_check.get()
                self.downloader.download_images(image_urls, download_images_pref, download_videos_pref)
                if index < len(urls) - 1 and not self.downloader.cancel_requested:
                # Si quedan más URLs y no se ha solicitado la cancelación, asegúrate de que el botón siga activo
                    self.cancel_button.configure(state="normal")
                else:
                    # Si es la última URL o se solicitó la cancelación, se puede desactivar el botón
                    self.cancel_button.configure(state="disabled")

            # Asegúrate de reactivar los widgets correctamente al finalizar todas las descargas
            self.enable_widgets()
            self.progress_label.configure(text=self.translations[self.current_language]["log_message_download_complete"])
        finally:
            self.is_downloading = False
            if self.closing:
                self.after(0, self.destroy)

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