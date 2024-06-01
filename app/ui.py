import json
import queue
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

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title("Downloader [V0.5.5]")
        self.setup_window()
        self.patch_notes = PatchNotes(self, self.tr)
        self.settings_window = SettingsWindow(self, self.tr, self.load_translations, self.update_ui_texts, self.save_language_preference)
        
        lang = self.load_language_preference()
        self.load_translations(lang)
        
        self.after(100, lambda: self.patch_notes.show_patch_notes(auto_show=True))
        self.initialize_ui()
        self.update_queue = queue.Queue()
        self.check_update_queue()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
    
    def on_app_close(self):
        if hasattr(self, 'active_downloader') and self.active_downloader:
            self.active_downloader.request_cancel()     
            self.active_downloader.shutdown_executors()     
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
        path = f"resources/config/languages/{lang}.json"
        with open(path, 'r', encoding='utf-8') as file:
            self.translations = json.load(file)
    
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

        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.pack(pady=10, fill='x', padx=20)

        self.download_speed_label = ctk.CTkLabel(self.action_frame, text=self.tr("Velocidad de descarga: 0 KB/s"))
        self.download_speed_label.pack(side='left', padx=10)

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

        # Menú Acerca de
        self.about_menu = tk.Menu(self.menubar, tearoff=0)
        self.about_menu.add_command(label=self.tr("Acerca de"), command=self.show_about)
        self.site_logos = {
            "Erome": "resources/img/logos/erome_logo.png",
            "Bunkr": "resources/img/logos/bunkr_logo.png",
            "Coomer.su": "resources/img/logos/coomer_logo.png",
            "Kemono.su": "resources/img/logos/kemono_logo.png",
        }
        self.menubar.add_cascade(label=self.tr("Acerca de"), menu=self.about_menu)
        self.about_menu.add_command(label=self.tr("Notas de Parche"), command=self.patch_notes.show_patch_notes)

        
    def update_ui_texts(self):
        # Actualizar controles de la UI
        self.url_label.configure(text=self.tr("URL de la página web:"))
        self.browse_button.configure(text=self.tr("Seleccionar Carpeta"))
        self.download_images_check.configure(text=self.tr("Descargar Imágenes"))
        self.download_videos_check.configure(text=self.tr("Descargar Vídeos"))
        self.download_button.configure(text=self.tr("Descargar"))
        self.cancel_button.configure(text=self.tr("Cancelar Descarga"))
        self.title(self.tr("Downloader [V0.5]"))
        
        # Actualizar textos del menú
        self.file_menu.entryconfigure(0, label=self.tr("Configuraciones"))
        self.file_menu.entryconfigure(2, label=self.tr("Salir"))
        self.favorites_menu.entryconfigure(0, label=self.tr("Añadir a Favoritos"))
        self.favorites_menu.entryconfigure(1, label=self.tr("Ver Favoritos"))
        self.about_menu.entryconfigure(0, label=self.tr("Acerca de"))
        self.about_menu.entryconfigure(1, label=self.tr("Notas de Parche"))

    def add_to_favorites(self):
        messagebox.showinfo(self.tr("Favoritos"), self.tr("coming_soon"))

    def show_favorites(self):
        messagebox.showinfo(self.tr("Favoritos"), self.tr("coming_soon"))

    def create_photoimage(self, path, size=(32, 32)):
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)  
        photoimg = ImageTk.PhotoImage(img)
        return photoimg

    def show_about(self):
        about_window = ctk.CTkToplevel(self)
        about_window.title("Acerca de")
        about_window.geometry("400x350")
        about_window.grab_set()
        
        title_label = ctk.CTkLabel(about_window, text="Downloader [V0.5.5]", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 5))

        description_label = ctk.CTkLabel(about_window, text=self.tr("Desarrollado por: Emy69\n\nCompatible con:"))
        description_label.pack(pady=(0, 20))
        
        for site, logo_path in self.site_logos.items():
            site_frame = ctk.CTkFrame(about_window)
            site_frame.pack(fill='x', padx=20, pady=5)
            
            logo_image = self.create_photoimage(logo_path)
            logo_label = tk.Label(site_frame, image=logo_image)  
            logo_label.image = logo_image 
            logo_label.pack(side='left', padx=10)
            
            site_label = ctk.CTkLabel(site_frame, text=site)
            site_label.pack(side='left')

        ok_button = ctk.CTkButton(about_window, text="OK", command=about_window.destroy)
        ok_button.pack(pady=10)
 
    def setup_erome_downloader(self):
        self.erome_downloader = EromeDownloader(
            root=self,
            enable_widgets_callback=self.enable_widgets,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Referer': 'https://www.erome.com/'
            },
            log_callback=self.add_log_message_safe,
            download_images=self.download_images_check.get(),
            download_videos=self.download_videos_check.get()
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
            download_videos=self.download_videos_check.get()
        )

        
        
    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.download_folder = folder_selected
            self.folder_path.configure(text=folder_selected)

    def start_download(self):
        url = self.url_entry.get("1.0", "end-1c").strip()
        if not hasattr(self, 'download_folder') or not self.download_folder:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, selecciona una carpeta de descarga."))
            return

        download_images = self.download_images_check.get() 
        download_videos = self.download_videos_check.get()

        # Habilita el botón de cancelar y deshabilita el botón de descarga
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        if "erome.com" in url:
            self.add_log_message_safe(self.tr("Descarga_Erome"))
            self.setup_erome_downloader()
            self.active_downloader = self.erome_downloader
            # Distingue entre descarga de perfil y álbum
            if "/a/" in url:
                # URL de álbum
                self.add_log_message_safe(self.tr("URL_album"))
                download_thread = threading.Thread(target=self.active_downloader.process_album_page, args=(url, self.download_folder, download_images, download_videos))
            else:
                # URL de perfil
                self.add_log_message_safe(self.tr("URL_perfil"))
                download_thread = threading.Thread(target=self.active_downloader.process_profile_page, args=(url, self.download_folder, download_images, download_videos))
        elif "bunkr.si" in url:
            self.add_log_message_safe(self.tr("Descarga_Bunkr"))
            self.setup_bunkr_downloader()
            self.active_downloader = self.bunkr_downloader
            download_thread = threading.Thread(target=self.bunkr_downloader.descargar_perfil_bunkr, args=(url,))
        elif "https://coomer.su/" in url or "https://kemono.su/" in url:
            self.add_log_message_safe(self.tr("Iniciando descarga..."))
            self.setup_general_downloader()
            self.active_downloader = self.general_downloader
            download_thread = threading.Thread(target=self.handle_download, args=(url,))
        else:
            self.add_log_message_safe(self.tr("enlaces_validos"))
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            return

        download_thread.start()
    
    def handle_download(self, url):
        image_urls, _, user_id = self.active_downloader.generate_image_links(url)
        self.active_downloader.download_media(image_urls, user_id, self.download_images_check.get(), self.download_videos_check.get())

    def cancel_download(self):
        # Control centralizado para cancelar descargas
        if self.active_downloader:
            self.active_downloader.request_cancel()
            self.add_log_message_safe("Cancelando la descarga...")
        else:
            self.add_log_message_safe("No hay una descarga en curso para cancelar.")
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