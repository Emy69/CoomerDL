import datetime
import json
import queue
import sys
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
from typing import Optional
from urllib.parse import ParseResult, parse_qs, urlparse
import webbrowser

import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image, ImageTk

from app.patch_notes import PatchNotes
from app.settings_window import SettingsWindow
from downloader.bunkr import BunkrDownloader
from downloader.downloader import Downloader
from downloader.erome import EromeDownloader

VERSION = "CoomerV0.6.3"
MAX_LOG_LINES = 100  # Límite máximo de líneas de log

def extract_ck_parameters(url: ParseResult) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get the service, user and post id from the url if they exist
    """
    match = re.search(r"/(?P<service>[^/?]+)(/user/(?P<user>[^/?]+)(/post/(?P<post>[^/?]+))?)?", url.path)
    if match:
        [site, service, post] = match.group("service", "user", "post")
        return site, service, post
    else:
        return None, None, None

def extract_ck_query(url: ParseResult) -> tuple[Optional[str], int]:
    """
    Try to obtain the query and offset from the url if they exist
    """

    # This is kinda contrived but query parameters are awful to get right
    query = parse_qs(url.query)
    q = query.get("q")[0] if query.get("q") is not None and len(query.get("q")) > 0 else None
    o = query.get("o")[0] if query.get("o") is not None and len(query.get("o")) > 0 else "0"

    return q, int(o) if str.isdigit(o) else 0

# Application class
class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title(f"Downloader [{VERSION}]")
        
        # Setup window
        self.setup_window()
        
        # Settings window
        self.settings_window = SettingsWindow(self, self.tr, self.load_translations, self.update_ui_texts, self.save_language_preference, VERSION, self.setup_general_downloader)

        # Load settings
        self.settings = self.settings_window.load_settings()
        
        # Language preferences
        lang = self.load_language_preference()
        self.load_translations(lang)

        # Patch notes
        self.patch_notes = PatchNotes(self, self.tr)

        self.progress_bars = {}
        #self.after(100, lambda: self.patch_notes.show_patch_notes(auto_show=True))
        
        # Initialize UI
        self.initialize_ui()
        
        self.update_ui_texts()  

        self.update_queue = queue.Queue()
        self.check_update_queue()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        self.download_start_time = None
        self.errors = []
        self.warnings = []
        self.max_downloads = self.settings_window.settings.get('max_downloads', 3)
        
        # Load download folder
        self.download_folder = self.load_download_folder() 
        if self.download_folder:
            self.folder_path.configure(text=self.download_folder)

        self.active_downloader = None  # Initialize active_downloader

    # Application close event
    def on_app_close(self):
        if self.is_download_active() and not self.active_downloader.cancel_requested:
            # Mostrar advertencia si hay una descarga activa
            messagebox.showwarning(
                self.tr("Descarga Activa"),
                self.tr("Hay una descarga en progreso. Por favor, cancela la descarga antes de cerrar.")
            )
        else:
            self.destroy()

    def is_download_active(self):
        return self.active_downloader is not None

    # Save and load language preferences
    def save_language_preference(self, language_code):
        config = {'language': language_code}
        with open('resources/config/languages/save_language/language_config.json', 'w') as config_file:
            json.dump(config, config_file)
        self.load_translations(language_code)
        self.update_ui_texts()
    
    def load_language_preference(self):
        try:
            with open('resources/config/languages/save_language/language_config.json', 'r') as config_file:
                config = json.load(config_file)
                return config.get('language', 'en')
        except FileNotFoundError:
            return 'en'

    # Load translations
    def load_translations(self, lang):
        path = "resources/config/languages/translations.json"
        with open(path, 'r', encoding='utf-8') as file:
            all_translations = json.load(file)
            self.translations = {key: value.get(lang, key) for key, value in all_translations.items()}
    
    def tr(self, text, **kwargs):
        translated_text = self.translations.get(text, text)
        if kwargs:
            translated_text = translated_text.format(**kwargs)
        return translated_text

    # Window setup
    def setup_window(self):
        window_width, window_height = 1000, 600
        center_x = int((self.winfo_screenwidth() / 2) - (window_width / 2))
        center_y = int((self.winfo_screenheight() / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        if sys.platform == "win32":
            self.iconbitmap("resources/img/window.ico")

    # Initialize UI components
    def initialize_ui(self):
        # Input frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill='x', padx=20, pady=20)
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_rowconfigure(1, weight=1)

        self.url_label = ctk.CTkLabel(self.input_frame, text=self.tr("URL de la página web:"))
        self.url_label.grid(row=0, column=0, sticky='w')

        self.url_entry = ctk.CTkEntry(self.input_frame)
        self.url_entry.grid(row=1, column=0, sticky='ew', padx=(0, 5))

        self.browse_button = ctk.CTkButton(self.input_frame, text=self.tr("Seleccionar Carpeta"), command=self.select_folder)
        self.browse_button.grid(row=1, column=1, sticky='e')

        self.folder_path = ctk.CTkLabel(self.input_frame, text="")
        self.folder_path.grid(row=2, column=0, columnspan=2, sticky='w')

        # Options frame
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, fill='x', padx=20)

        self.download_images_check = ctk.CTkCheckBox(self.options_frame, text=self.tr("Descargar Imágenes"))
        self.download_images_check.pack(side='left', padx=10)
        self.download_images_check.select()

        self.download_videos_check = ctk.CTkCheckBox(self.options_frame, text=self.tr("Descargar Vídeos"))
        self.download_videos_check.pack(side='left', padx=10)
        self.download_videos_check.select()

        self.download_compressed_check = ctk.CTkCheckBox(self.options_frame, text=self.tr("Descargar Comprimidos"))
        self.download_compressed_check.pack(side='left', padx=10)
        self.download_compressed_check.select()

        # Action frame
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.pack(pady=10, fill='x', padx=20)

        self.download_button = ctk.CTkButton(self.action_frame, text=self.tr("Descargar"), command=self.start_download)
        self.download_button.pack(side='left', padx=10)

        self.cancel_button = ctk.CTkButton(self.action_frame, text=self.tr("Cancelar Descarga"), state="disabled", command=self.cancel_download)
        self.cancel_button.pack(side='left', padx=10)

        self.progress_label = ctk.CTkLabel(self.action_frame, text="")
        self.progress_label.pack(side='left', padx=10)

        self.log_textbox = ctk.CTkTextbox(self, width=590, height=200, state='disabled')
        self.log_textbox.pack(pady=(10, 0), padx=20, fill='both', expand=True)

        self.download_all_check = ctk.CTkCheckBox(self.action_frame)
        self.download_all_check.pack(side='left', padx=10)
        
        # Conectar el evento del checkbox con una función de actualización
        self.download_all_check.configure(command=self.update_info_text)
        
        self.update_info_text()

        # Progress frame
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.pack(pady=(0, 10), fill='x', padx=20)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.processing_label = ctk.CTkLabel(self.progress_frame, text=self.tr("Procesando videos..."), font=("Arial", 12))
        self.processing_label.pack(side='top', pady=(0, 10))
        self.processing_label.pack_forget()

        self.progress_percentage = ctk.CTkLabel(self.progress_frame, text="0%")
        self.progress_percentage.pack(side='left')

        self.toggle_details_button = ctk.CTkButton(self.progress_frame, text="...", width=5, command=self.toggle_progress_details)
        self.toggle_details_button.pack(side='left', padx=(5, 0))

        self.progress_details_frame = ctk.CTkFrame(self)
        self.progress_details_frame.place_forget()

        # Context menu
        self.context_menu = tk.Menu(self.url_entry, tearoff=0)
        self.context_menu.add_command(label=self.tr("Copiar"), command=self.copy_to_clipboard)
        self.context_menu.add_command(label=self.tr("Pegar"), command=self.paste_from_clipboard)
        self.context_menu.add_command(label=self.tr("Cortar"), command=self.cut_to_clipboard)

        self.url_entry.bind("<Button-3>", self.show_context_menu)

        # Menubar
        self.create_menubar()

        footer = ctk.CTkFrame(self, height=30, corner_radius=0)
        footer.pack(side="bottom", fill="x")

        self.footer_eta_label = ctk.CTkLabel(footer, text="", font=("Arial", 10))
        self.footer_eta_label.pack(side="left", padx=20)

        self.footer_speed_label = ctk.CTkLabel(footer, text="", font=("Arial", 10))
        self.footer_speed_label.pack(side="right", padx=20)

        # Actualizar textos después de inicializar la UI
        self.update_ui_texts()

    def update_info_text(self):
        if self.download_all_check.get():
            self.download_all_check.configure(text=self.tr("Descargar todo el perfil"))
        else:
            self.download_all_check.configure(text=self.tr("Descargar solo los posts del URL proporcionado"))

    # Update UI texts
    def update_ui_texts(self):
        self.url_label.configure(text=self.tr("URL de la página web:"))
        self.browse_button.configure(text=self.tr("Seleccionar Carpeta"))
        self.download_images_check.configure(text=self.tr("Descargar Imágenes"))
        self.download_videos_check.configure(text=self.tr("Descargar Vídeos"))
        self.download_compressed_check.configure(text=self.tr("Descargar Comprimidos"))
        self.download_button.configure(text=self.tr("Descargar"))
        self.cancel_button.configure(text=self.tr("Cancelar Descarga"))
        self.processing_label.configure(text=self.tr("Procesando videos..."))
        self.title(self.tr(f"Downloader [{VERSION}]"))

        self.file_menu.entryconfigure(0, label=self.tr("Configuraciones"))
        self.file_menu.entryconfigure(2, label=self.tr("Salir"))
        self.update_info_text()

    def create_menubar(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # Menú Archivo
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label=self.tr("Configuraciones"), command=self.settings_window.open_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr("Salir"), command=self.quit)
        self.menubar.add_cascade(label=self.tr("Archivo"), menu=self.file_menu)

        # Menú Reportar un error
        self.report_menu = tk.Menu(self.menubar, tearoff=0)
        self.report_menu.add_command(label=self.tr("GitHub"), command=lambda: webbrowser.open("https://github.com/Emy69/CoomerDL/issues"))
        self.report_menu.add_command(label=self.tr("Discord"), command=lambda: webbrowser.open("https://discord.gg/ku8gSPsesh"))
        self.menubar.add_cascade(label=self.tr("Reportar un error"), menu=self.report_menu)

        # Menú Donaciones
        self.donate_menu = tk.Menu(self.menubar, tearoff=0)
        self.donate_menu.add_command(label=self.tr("PayPal"), command=lambda: webbrowser.open("https://www.paypal.com/paypalme/Emy699"))
        self.menubar.add_cascade(label=self.tr("Donaciones"), menu=self.donate_menu)

        # Menú Notas
        self.notes_menu = tk.Menu(self.menubar, tearoff=0)
        self.notes_menu.add_command(label=self.tr("love u"), command=self.open_patch_notes)
        self.menubar.add_cascade(label=self.tr("<3"), menu=self.notes_menu)
    
    def open_patch_notes(self):
        self.patch_notes.show_patch_notes()

    # Image processing
    def create_photoimage(self, path, size=(32, 32)):
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)
        photoimg = ImageTk.PhotoImage(img)
        return photoimg

    # Setup downloaders
    def setup_erome_downloader(self, is_profile_download=False):
        self.erome_downloader = EromeDownloader(
            root=self,
            enable_widgets_callback=self.enable_widgets,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Referer': 'https://www.erome.com/'
            },
            log_callback=self.add_log_message_safe,
            update_progress_callback=self.update_progress,
            update_global_progress_callback=self.update_global_progress,
            download_images=self.download_images_check.get(),
            download_videos=self.download_videos_check.get(),
            is_profile_download=is_profile_download,
            max_workers=self.max_downloads,
            tr=self.tr
        )

    def setup_bunkr_downloader(self):
        self.bunkr_downloader = BunkrDownloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message_safe,
            enable_widgets_callback=self.enable_widgets,
            update_progress_callback=self.update_progress,
            update_global_progress_callback=self.update_global_progress,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Referer': 'https://bunkr.si/',
            },
            max_workers=self.max_downloads
        )

    def setup_general_downloader(self):
        self.general_downloader = Downloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message_safe,
            enable_widgets_callback=self.enable_widgets,
            update_progress_callback=self.update_progress,
            update_global_progress_callback=self.update_global_progress,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Referer': 'https://coomer.su/',
            },
            download_images=self.download_images_check.get(),
            download_videos=self.download_videos_check.get(),
            download_compressed=self.download_compressed_check.get(),
            tr=self.tr,
            max_workers=self.max_downloads,
            folder_structure=self.settings_window.settings.get('folder_structure', 'default')
        )

    # Folder selection
    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.download_folder = folder_selected
            self.folder_path.configure(text=folder_selected)
            self.save_download_folder(folder_selected)
    
    # Progress management
    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None):
        if total > 0:
            percentage = (downloaded / total) * 100
            if file_id is None:
                self.progress_bar.set(downloaded / total)
                self.progress_percentage.configure(text=f"{percentage:.2f}%")
            else:
                if file_id not in self.progress_bars:
                    progress_bar_frame = ctk.CTkFrame(self.progress_details_frame)
                    progress_label = ctk.CTkLabel(progress_bar_frame, text=file_path)
                    progress_bar = ctk.CTkProgressBar(progress_bar_frame)
                    self.progress_bars[file_id] = (progress_bar, progress_bar_frame)
                    progress_label.pack(fill='x')
                    progress_bar.pack(fill='x')
                    progress_bar_frame.pack(fill='x', padx=10, pady=5)
                self.progress_bars[file_id][0].set(downloaded / total)
                if downloaded >= total:
                    self.after(2000, lambda: self.remove_progress_bar(file_id))
        else:
            if file_id is None:
                self.progress_bar.set(0)
                self.progress_percentage.configure(text="0%")
            else:
                if file_id in self.progress_bars:
                    self.progress_bars[file_id][0].set(0)

        if speed is not None and eta is not None:
            speed_text = f"Speed: {speed / 1024:.2f} KB/s" if speed < 1048576 else f"Speed: {speed / 1048576:.2f} MB/s"
            eta_text = f"ETA: {int(eta // 60)}m {int(eta % 60)}s"
            self.footer_speed_label.configure(text=speed_text)
            self.footer_eta_label.configure(text=eta_text)

    def remove_progress_bar(self, file_id):
        if file_id in self.progress_bars:
            self.progress_bars[file_id][1].pack_forget()
            del self.progress_bars[file_id]

    def update_global_progress(self, completed_files, total_files):
        if total_files > 0:
            percentage = (completed_files / total_files) * 100
            self.progress_bar.set(completed_files / total_files)
            self.progress_percentage.configure(text=f"{percentage:.2f}%")

    def toggle_progress_details(self):
        if self.progress_details_frame.winfo_ismapped():
            self.progress_details_frame.place_forget()
        else:
            self.progress_details_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.progress_details_frame.lift()

    def center_progress_details_frame(self):
        self.progress_details_frame.update_idletasks()
        width = self.progress_details_frame.winfo_width()
        height = self.progress_details_frame.winfo_height()
        x = (self.winfo_width() // 2) - (width // 2)
        y = (self.winfo_height() // 2) - (height // 2)
        self.progress_details_frame.place(x=x, y=y, anchor='nw')

    # Error logging
    def log_error(self, error_message):
        self.errors.append(error_message)
        self.add_log_message_safe(f"Error: {error_message}")

    def wrapped_download(self, download_method, *args):
        try:
            download_method(*args)
        finally:
            self.active_downloader = None  # Resetea la active_downloader cuando la descarga termina
            self.enable_widgets()  # Asegúrate de habilitar los widgets
            self.export_logs()  # Llama a export_logs al finalizar la descarga

    # Download management
    def start_download(self):
        url = self.url_entry.get().strip()
        if not hasattr(self, 'download_folder') or not self.download_folder:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, selecciona una carpeta de descarga."))
            return

        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.processing_label.pack()
        self.download_start_time = datetime.datetime.now()
        self.errors = []
        download_all = self.download_all_check.get()

        parsed_url = urlparse(url)
        if "erome.com" in url:
            self.add_log_message_safe(self.tr("Descargando Erome"))
            is_profile_download = "/a/" not in url
            self.setup_erome_downloader(is_profile_download=is_profile_download)
            self.active_downloader = self.erome_downloader
            if "/a/" in url:
                self.add_log_message_safe(self.tr("URL del álbum"))
                download_thread = threading.Thread(target=self.wrapped_download, args=(self.active_downloader.process_album_page, url, self.download_folder, self.download_images_check.get(), self.download_videos_check.get()))
            else:
                self.add_log_message_safe(self.tr("URL del perfil"))
                download_thread = threading.Thread(target=self.wrapped_download, args=(self.active_downloader.process_profile_page, url, self.download_folder, self.download_images_check.get(), self.download_videos_check.get()))
        elif re.search(r"https?://([a-z0-9-]+\.)?bunkr\.[a-z]{2,}", url):
            self.add_log_message_safe(self.tr("Descargando Bunkr"))
            self.setup_bunkr_downloader()
            self.active_downloader = self.bunkr_downloader
            if "/v/" in url or "/i/" in url:
                self.add_log_message_safe(self.tr("URL del post"))
                download_thread = threading.Thread(target=self.wrapped_download, args=(self.bunkr_downloader.descargar_post_bunkr, url))
            else:
                self.add_log_message_safe(self.tr("URL del perfil"))
                download_thread = threading.Thread(target=self.wrapped_download, args=(self.bunkr_downloader.descargar_perfil_bunkr, url))
        elif parsed_url.netloc in ["coomer.su", "kemono.su"]:
            self.add_log_message_safe(self.tr("Iniciando descarga..."))
            self.setup_general_downloader()
            self.active_downloader = self.general_downloader

            site = f"{parsed_url.netloc}"
            service, user, post = extract_ck_parameters(parsed_url)
            if service is None or user is None:
                if service is None:
                    self.add_log_message_safe(self.tr("No se pudo extraer el servicio."))
                    messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el servicio."))
                else:
                    self.add_log_message_safe(self.tr("No se pudo extraer el ID del usuario."))
                    messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el ID del usuario."))

                self.add_log_message_safe(self.tr("URL no válida"))
                self.download_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
                self.processing_label.pack_forget()
                return

            self.add_log_message_safe(self.tr("Servicio extraído: {service} del sitio: {site}", service=service, site=site))

            if post is not None:
                self.add_log_message_safe(self.tr("Descargando post único..."))
                download_thread = threading.Thread(target=self.wrapped_download, args=(self.start_ck_post_download, site, service, user, post))
            else:
                query, offset = extract_ck_query(parsed_url)
                self.add_log_message_safe(self.tr("Descargando todo el contenido del usuario..." if download_all else "Descargando solo los posts del URL proporcionado..."))
                download_thread = threading.Thread(target=self.wrapped_download, args=(self.start_ck_profile_download, site, service, user, query, download_all, offset))
        else:
            self.add_log_message_safe(self.tr("URL no válida"))
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            self.processing_label.pack_forget()
            return

        download_thread.start()

    def start_ck_profile_download(self, site, service, user, query, download_all, initial_offset):
        download_info = self.active_downloader.download_media(site, user, service, query=query, download_all=download_all, initial_offset=initial_offset)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
        # Llamar a export_logs al finalizar la descarga
        self.export_logs()
        self.active_downloader = None  # Resetea la active_downloader cuando la descarga termina
        self.enable_widgets()  # Asegúrate de habilitar los widgets
    
    def start_ck_post_download(self, site, service, user, post):
        download_info = self.active_downloader.download_single_post(site, post, service, user)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
        # Llamar a export_logs al finalizar la descarga
        self.export_logs()
        self.active_downloader = None  # Resetea la active_downloader cuando la descarga termina
        self.enable_widgets()  # Asegúrate de habilitar los widgets

    def extract_user_id(self, url):
        self.add_log_message_safe(self.tr("Extrayendo ID del usuario del URL: {url}", url=url))
        match = re.search(r'/user/([^/?]+)', url)
        if match:
            user_id = match.group(1)
            self.add_log_message_safe(self.tr("ID del usuario extraído: {user_id}", user_id=user_id))
            return user_id
        else:
            self.add_log_message_safe(self.tr("No se pudo extraer el ID del usuario."))
            messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el ID del usuario."))
            return None

    def extract_post_id(self, url):
        match = re.search(r'/post/([^/?]+)', url)
        if match:
            post_id = match.group(1)
            self.add_log_message_safe(self.tr("ID del post extraído: {post_id}", post_id=post_id))
            return post_id
        else:
            self.add_log_message_safe(self.tr("No se pudo extraer el ID del post."))
            messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el ID del post."))
            return None

    def cancel_download(self):
        if self.active_downloader:
            self.active_downloader.request_cancel()
            self.active_downloader = None
            self.clear_progress_bars()
        else:
            self.add_log_message_safe(self.tr("No hay una descarga en curso para cancelar."))
        self.enable_widgets()

    def clear_progress_bars(self):
        for file_id in list(self.progress_bars.keys()):
            self.remove_progress_bar(file_id)

    # Log messages safely
    def add_log_message_safe(self, message):
        if "error" in message.lower():
            self.errors.append(message)
        if "warning" in message.lower():
            self.warnings.append(message)

        def log_in_main_thread():
            self.log_textbox.configure(state='normal')
            self.log_textbox.insert('end', message + '\n')
            self.limit_log_lines() 
            self.log_textbox.configure(state='disabled')
            self.log_textbox.yview_moveto(1)
        self.after(0, log_in_main_thread)

    def limit_log_lines(self):
        log_lines = self.log_textbox.get("1.0", "end-1c").split("\n")
        if len(log_lines) > MAX_LOG_LINES:
            self.log_textbox.configure(state='normal')
            self.log_textbox.delete("1.0", f"{len(log_lines) - MAX_LOG_LINES}.0")
            self.log_textbox.configure(state='disabled')

    # Export logs to a file
    def export_logs(self):
        log_folder = "resources/config/logs/"
        Path(log_folder).mkdir(parents=True, exist_ok=True)
        log_file_path = Path(log_folder) / f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            if self.active_downloader:
                total_files = self.active_downloader.total_files
                completed_files = self.active_downloader.completed_files
                skipped_files = self.active_downloader.skipped_files
                failed_files = self.active_downloader.failed_files
            else:
                total_files = 0
                completed_files = 0
                skipped_files = []
                failed_files = []
            
            total_images = completed_files if self.download_images_check.get() else 0
            total_videos = completed_files if self.download_videos_check.get() else 0
            errors = len(self.errors)
            warnings = len(self.warnings)
            duration = datetime.datetime.now() - self.download_start_time

            skipped_files_summary = "\n".join(skipped_files)
            failed_files_summary = "\n".join(failed_files)

            summary = (
                f"{self.tr('Total de archivos descargados')}: {total_files}\n"
                f"{self.tr('Total de imágenes descargadas')}: {total_images}\n"
                f"{self.tr('Total de videos descargados')}: {total_videos}\n"
                f"{self.tr('Errores')}: {errors}\n"
                f"{self.tr('Advertencias')}: {warnings}\n"
                f"{self.tr('Tiempo total de descarga')}: {duration}\n\n"
                f"{self.tr('Archivos saltados por ya estar descargados')}:\n{skipped_files_summary}\n\n"
                f"{self.tr('Archivos fallidos')}:\n{failed_files_summary}\n\n"
            )

            with open(log_file_path, 'w') as file:
                file.write(summary)
                file.write(self.log_textbox.get("1.0", tk.END))
            self.add_log_message_safe(self.tr("Logs exportados exitosamente a {path}", path=log_file_path))
        except Exception as e:
            self.add_log_message_safe(self.tr(f"No se pudo exportar los logs: {e}"))

    # Clipboard operations
    def copy_to_clipboard(self):
        try:
            selected_text = self.url_entry.selection_get()
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
            else:
                self.add_log_message_safe(self.tr("No hay texto seleccionado para copiar."))
        except tk.TclError:
            self.add_log_message_safe(self.tr("No hay texto seleccionado para copiar."))

    def paste_from_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                try:
                    self.url_entry.delete("sel.first", "sel.last")  # Elimina el texto seleccionado si hay alguno
                except tk.TclError:
                    pass
                self.url_entry.insert(tk.INSERT, clipboard_text)
            else:
                self.add_log_message_safe(self.tr("No hay texto en el portapapeles para pegar."))
        except tk.TclError as e:
            self.add_log_message_safe(self.tr(f"Error al pegar desde el portapapeles: {e}"))

    def cut_to_clipboard(self):
        try:
            selected_text = self.url_entry.selection_get()
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.url_entry.delete("sel.first", "sel.last")
            else:
                self.add_log_message_safe(self.tr("No hay texto seleccionado para cortar."))
        except tk.TclError:
            self.add_log_message_safe(self.tr("No hay texto seleccionado para cortar."))


    # Show context menu
    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.context_menu.grab_release()

    # Update queue
    def check_update_queue(self):
        while not self.update_queue.empty():
            task = self.update_queue.get_nowait()
            task()
        self.after(100, self.check_update_queue)

    # Enable widgets
    def enable_widgets(self):
        self.update_queue.put(lambda: self.download_button.configure(state="normal"))
        self.update_queue.put(lambda: self.cancel_button.configure(state="disabled"))
        self.update_queue.put(lambda: self.download_all_check.configure(state="normal"))

    # Save and load download folder
    def save_download_folder(self, folder_path):
        config = {'download_folder': folder_path}
        with open('resources/config/download_path/download_folder.json', 'w') as config_file:
            json.dump(config, config_file)

    def load_download_folder(self):
        config_path = 'resources/config/download_path/download_folder.json'
        config_dir = Path(config_path).parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True)
        if not Path(config_path).exists():
            with open(config_path, 'w') as config_file:
                json.dump({'download_folder': ''}, config_file)
        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
                return config.get('download_folder', '')
        except json.JSONDecodeError:
            return ''

    # Update max downloads
    def update_max_downloads(self, max_downloads):
        self.max_downloads = max_downloads