import json
import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import Image, scrolledtext
import customtkinter as ctk
from tkinter import PhotoImage
from tkinter import filedialog, messagebox
from customtkinter import CTkImage
from PIL import Image, ImageTk

from .patch_notes import PatchNotes
from downloader.erome import EromeDownloader
from downloader.downloader import Downloader
from downloader.bunkr import BunkrDownloader
from .settings_window import SettingsWindow

# Definir la versión como una variable global
VERSION = "CoomerV0.6.0"

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title(f"Downloader [{VERSION}]")
        self.setup_window()
        self.patch_notes = PatchNotes(self, self.tr)
        self.settings_window = SettingsWindow(self, self.tr, self.load_translations, self.update_ui_texts, self.save_language_preference, VERSION)
        
        lang = self.load_language_preference()
        self.load_translations(lang)

        
        self.after(100, lambda: self.patch_notes.show_patch_notes(auto_show=True))
        self.initialize_ui()
        self.update_queue = queue.Queue()
        self.check_update_queue()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        
        self.download_folder = self.load_download_folder() 
        if self.download_folder:
            self.folder_path.configure(text=self.download_folder)

    def on_app_close(self):
        if hasattr(self, 'active_downloader') and self.active_downloader:
            self.active_downloader.request_cancel()
            self.active_downloader.shutdown_executor()
        self.destroy()

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

    def load_translations(self, lang):
        path = "resources/config/languages/translations.json"
        with open(path, 'r', encoding='utf-8') as file:
            all_translations = json.load(file)
            self.translations = {key: value.get(lang, key) for key, value in all_translations.items()}
    
    def tr(self, text):
        return self.translations.get(text, text)

    def setup_window(self):
        window_width, window_height = 1000, 680
        center_x = int((self.winfo_screenwidth() / 2) - (window_width / 2))
        center_y = int((self.winfo_screenheight() / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.iconbitmap("resources/img/window.ico")

    def initialize_ui(self):
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill='x', padx=20, pady=20)

        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_rowconfigure(1, weight=1)

        self.url_label = ctk.CTkLabel(self.input_frame, text=self.tr("URL de la página web:"))
        self.url_label.grid(row=0, column=0, sticky='w')

        self.url_entry = ctk.CTkTextbox(self.input_frame, height=80, wrap="none")
        self.url_entry.grid(row=1, column=0, sticky='ew', padx=(0, 5))

        self.browse_button = ctk.CTkButton(self.input_frame, height=80, text=self.tr("Seleccionar Carpeta"), command=self.select_folder)
        self.browse_button.grid(row=1, column=1, sticky='e')

        self.folder_path = ctk.CTkLabel(self.input_frame, text="")
        self.folder_path.grid(row=3, column=0, columnspan=2, sticky='w')

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

        self.context_menu = tk.Menu(self.url_entry, tearoff=0)
        self.context_menu.add_command(label=self.tr("Pegar"), command=self.paste_from_clipboard)

        self.url_entry.bind("<Button-3>", self.show_context_menu)

        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # Menú Archivo
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label=self.tr("Configuraciones"), command=self.settings_window.open_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr("Salir"), command=self.quit)
        self.menubar.add_cascade(label=self.tr("Archivo"), menu=self.file_menu)

        # Menú Favoritos
        self.favorites_menu = tk.Menu(self.menubar, tearoff=0)
        self.favorites_menu.add_command(label=self.tr("Añadir a Favoritos"), command=self.add_to_favorites)
        self.favorites_menu.add_command(label=self.tr("Ver Favoritos"), command=self.show_favorites)
        self.menubar.add_cascade(label=self.tr("Favoritos"), menu=self.favorites_menu)

    def update_ui_texts(self):
        self.url_label.configure(text=self.tr("URL de la página web:"))
        self.browse_button.configure(text=self.tr("Seleccionar Carpeta"))
        self.download_images_check.configure(text=self.tr("Descargar Imágenes"))
        self.download_videos_check.configure(text=self.tr("Descargar Vídeos"))
        self.download_compressed_check.configure(text=self.tr("Descargar Comprimidos"))
        self.download_button.configure(text=self.tr("Descargar"))
        self.cancel_button.configure(text=self.tr("Cancelar Descarga"))
        self.title(self.tr(f"Downloader [{VERSION}]"))

        self.file_menu.entryconfigure(0, label=self.tr("Configuraciones"))
        self.file_menu.entryconfigure(2, label=self.tr("Salir"))
        self.favorites_menu.entryconfigure(0, label=self.tr("Añadir a Favoritos"))
        self.favorites_menu.entryconfigure(1, label=self.tr("Ver Favoritos"))

    def add_to_favorites(self):
        messagebox.showinfo(self.tr("Favoritos"), self.tr("coming_soon"))

    def show_favorites(self):
        messagebox.showinfo(self.tr("Favoritos"), self.tr("coming_soon"))

    def create_photoimage(self, path, size=(32, 32)):
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)
        photoimg = ImageTk.PhotoImage(img)
        return photoimg

    def setup_erome_downloader(self):
        self.erome_downloader = EromeDownloader(
            root=self,
            enable_widgets_callback=self.enable_widgets,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, как Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Referer': 'https://www.erome.com/'
            },
            log_callback=self.add_log_message_safe
        )

    def setup_bunkr_downloader(self):
        self.bunkr_downloader = BunkrDownloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message_safe,
            enable_widgets_callback=self.enable_widgets,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Referer': 'https://bunkr.si/',
            }
        )
    
    def setup_general_downloader(self):
        self.general_downloader = Downloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message_safe,
            enable_widgets_callback=self.enable_widgets,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Referer': 'https://coomer.su/',
            },
            download_images=self.download_images_check.get(),
            download_videos=self.download_videos_check.get(),
            download_compressed=self.download_compressed_check.get()
        )

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.download_folder = folder_selected
            self.folder_path.configure(text=folder_selected)
            self.save_download_folder(folder_selected)

    def start_download(self):
        url = self.url_entry.get("1.0", "end-1c").strip()
        if not hasattr(self, 'download_folder') or not self.download_folder:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, selecciona una carpeta de descarga."))
            return

        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        if "erome.com" in url:
            self.add_log_message_safe(self.tr("Descargando Erome"))
            self.setup_erome_downloader()
            self.active_downloader = self.erome_downloader
            if "/a/" in url:
                self.add_log_message_safe(self.tr("URL del álbum"))
                download_thread = threading.Thread(target=self.active_downloader.process_album_page, args=(url, self.download_folder))
            else:
                self.add_log_message_safe(self.tr("URL del perfil"))
                download_thread = threading.Thread(target=self.active_downloader.process_profile_page, args=(url, self.download_folder))
        elif "bunkr.si" in url:
            self.add_log_message_safe(self.tr("Descargando Bunkr"))
            self.setup_bunkr_downloader()
            self.active_downloader = self.bunkr_downloader
            download_thread = threading.Thread(target=self.bunkr_downloader.descargar_perfil_bunkr, args=(url,))
        elif "https://coomer.su/" in url or "https://kemono.su/" in url:
            self.add_log_message_safe(self.tr("Iniciando descarga..."))
            self.setup_general_downloader()
            self.active_downloader = self.general_downloader
            site, service = self.extract_service(url)

            # Detectar si es un post o todo el contenido del usuario
            if re.match(r"https://(coomer|kemono).su/.+/user/.+/post/.+", url):
                self.add_log_message_safe(self.tr("Descargando post único..."))
                download_thread = threading.Thread(target=self.start_post_download, args=(url, site, service))
            else:
                self.add_log_message_safe(self.tr("Descargando todo el contenido del usuario..."))
                if messagebox.askyesno(self.tr("Descargar todo el contenido"), self.tr("¿Desea descargar todo el contenido del usuario?")):
                    download_all = True
                else:
                    download_all = False
                download_thread = threading.Thread(target=self.start_profile_download, args=(url, site, service, download_all))
        else:
            self.add_log_message_safe(self.tr("URL no válida"))
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            return

        download_thread.start()

    def start_profile_download(self, url, site, service, download_all):
        user_id = self.extract_user_id(url)
        if user_id:
            self.active_downloader.download_media(site, user_id, service, download_all)

    def start_post_download(self, url, site, service):
        post_id = self.extract_post_id(url)
        user_id = self.extract_user_id(url)
        if post_id and user_id:
            self.active_downloader.download_single_post(site, post_id, service, user_id)

    def extract_service(self, url):
        match = re.search(r"https://(coomer|kemono).su/([^/]+)/user", url)
        if match:
            site = match.group(1)
            service = match.group(2)
            self.add_log_message_safe(self.tr(f"Servicio extraído: {service} del sitio: {site}"))
            return site, service
        else:
            self.add_log_message_safe(self.tr("No se pudo extraer el servicio."))
            messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el servicio."))
            return None, None

    def extract_user_id(self, url):
        self.add_log_message_safe(self.tr(f"Extrayendo ID del usuario del URL: {url}"))
        match = re.search(r'/user/([^/?]+)', url)
        if match:
            user_id = match.group(1)
            self.add_log_message_safe(self.tr(f"ID del usuario extraído: {user_id}"))
            return user_id
        else:
            self.add_log_message_safe(self.tr("No se pudo extraer el ID del usuario."))
            messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el ID del usuario."))
            return None

    def extract_post_id(self, url):
        match = re.search(r'/post/([^/?]+)', url)
        if match:
            post_id = match.group(1)
            self.add_log_message_safe(self.tr(f"ID del post extraído: {post_id}"))
            return post_id
        else:
            self.add_log_message_safe(self.tr("No se pudo extraer el ID del post."))
            messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el ID del post."))
            return None

    def cancel_download(self):
        if self.active_downloader:
            self.active_downloader.request_cancel()
            self.add_log_message_safe(self.tr("Cancelando la descarga..."))
        else:
            self.add_log_message_safe(self.tr("No hay una descarga en curso para cancelar."))
        self.enable_widgets()

    def add_log_message_safe(self, message):
        def log_in_main_thread():
            self.log_textbox.configure(state='normal')
            self.log_textbox.insert('end', message + '\n')
            self.log_textbox.configure(state='disabled')
            self.log_textbox.yview_moveto(1)
        self.after(0, log_in_main_thread)

    def paste_from_clipboard(self):
        try:
            self.url_entry.delete("1.0", tk.END)
            self.url_entry.insert(tk.END, self.clipboard_get())
        except tk.TclError:
            pass

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def check_update_queue(self):
        while not self.update_queue.empty():
            task = self.update_queue.get_nowait()
            task()
        self.after(100, self.check_update_queue)

    def enable_widgets(self):
        self.update_queue.put(lambda: self.download_button.configure(state="normal"))
        self.update_queue.put(lambda: self.cancel_button.configure(state="disabled"))

    def save_download_folder(self, folder_path):
        config = {'download_folder': folder_path}
        with open('resources/config/download_path/download_folder.json', 'w') as config_file:
            json.dump(config, config_file)

    def load_download_folder(self):
        config_path = 'resources/config/download_path/download_folder.json'
        if not Path(config_path).exists:
            with open(config_path, 'w') as config_file:
                json.dump({}, config_file)
        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
                return config.get('download_folder', '')
        except json.JSONDecodeError:
            return ''