import datetime
import json
import queue
import sys
import re
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Tuple
from urllib.parse import ParseResult, parse_qs, urlparse
import webbrowser
import requests
from PIL import Image, ImageTk
import customtkinter as ctk
import psutil

# Importaciones de módulos personalizados
from app.settings_window import SettingsWindow
from app.about_window import AboutWindow
from downloader.bunkr import BunkrDownloader
from downloader.downloader import Downloader
from downloader.erome import EromeDownloader
from downloader.simpcity import SimpCity
from downloader.jpg5 import Jpg5Downloader
from app.progress_manager import ProgressManager

VERSION = "V0.8.4"
MAX_LOG_LINES = 50  # Límite máximo de líneas de log

def extract_ck_parameters(url: ParseResult) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Obtiene el servicio, usuario y ID de post del URL si existen.
    """
    match = re.search(r"/(?P<service>[^/?]+)(/user/(?P<user>[^/?]+)(/post/(?P<post>[^/?]+))?)?", url.path)
    if match:
        site, service, post = match.group("service", "user", "post")
        return site, service, post
    return None, None, None

def extract_ck_query(url: ParseResult) -> Tuple[Optional[str], int]:
    """
    Intenta obtener la consulta y el offset del URL si existen.
    """
    query = parse_qs(url.query)
    q = query.get("q", [None])[0]
    o = query.get("o", ["0"])[0]
    return q, int(o) if o.isdigit() else 0

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.errors = []
        self.warnings = []
        self.title(f"Downloader [{VERSION}]")
        # Inicializar atributos
        self.settings_window = SettingsWindow(self, self.tr, self.load_translations, self.update_ui_texts, self.save_language_preference, VERSION, self)
        self.about_window = AboutWindow(self, self.tr, VERSION)
        self.settings = self.settings_window.load_settings()
        lang = self.load_language_preference()
        self.load_translations(lang)
        self.image_downloader = None
        self.progress_bars = {}
        #self.github_stars = self.get_github_stars("emy69", "CoomerDL")
        self.github_icon = self.load_icon("resources/img/github-logo-24.png", "GitHub", size=(16, 16))
        self.discord_icon = self.load_icon("resources/img/discord-alt-logo-24.png", "Discord", size=(16, 16))
        self.new_icon = self.load_icon("resources/img/dollar-circle-solid-24.png", "New Icon", size=(16, 16))
        self.download_folder = self.load_download_folder()
        self.active_downloader = None
        self.max_downloads = self.settings_window.settings.get('max_downloads', 3)

        self.icons = {
            'image': self.load_and_resize_image('resources/img/image_icon.png', (40, 40)),
            'video': self.load_and_resize_image('resources/img/video_icon.png', (40, 40)),
            'zip': self.load_and_resize_image('resources/img/zip_icon.png', (40, 40)),
            'default': self.load_and_resize_image('resources/img/default_icon.png', (40, 40))
        }
        
        
        # Configurar la ventana principal
        self.setup_window()
        self.initialize_ui()
        self.update_ui_texts()
        
        # Configurar cola de actualización
        self.update_queue = queue.Queue()
        self.check_update_queue()
        
        # Configurar eventos de cierre
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)
        
        # Inicializar manager de progreso
        self.progress_manager = ProgressManager(
            root=self,
            icons=self.icons,
            footer_speed_label=self.footer_speed_label,
            footer_eta_label=self.footer_eta_label,
            progress_bar=self.progress_bar,
            progress_percentage=self.progress_percentage
        )
        
        # Configurar carpeta de descarga
        if self.download_folder:
            self.folder_path.configure(text=self.download_folder)
    
    def setup_window(self):
        """
        Configura las propiedades iniciales de la ventana.
        """
        window_width, window_height = 1000, 600
        center_x = (self.winfo_screenwidth() - window_width) // 2
        center_y = (self.winfo_screenheight() - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.minsize(window_width, window_height)
        if sys.platform == "win32":
            self.iconbitmap("resources/img/window.ico")
    
    def initialize_ui(self):
        """
        Inicializa todos los componentes de la interfaz de usuario.
        """
        self.create_menu_bar()
        self.create_input_frame()
        self.create_options_frame()
        self.create_action_frame()
        self.create_log_textbox()
        self.create_progress_frame()
        self.create_footer()
        self.create_context_menu()
    
    def create_menu_bar(self):
        """
        Crea la barra de menú personalizada.
        """
        self.menu_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.menu_bar.pack(side="top", fill="x")
        self.create_custom_menubar()
    
    def create_custom_menubar(self):
        """
        Añade botones y iconos personalizados a la barra de menú.
        """
        # Botones de menú principales
        self.add_menu_button("Archivo", self.toggle_archivo_menu)
        self.add_menu_button("About", self.about_window.show_about)
        
        # Añadir iconos personalizados
        #self.add_icon_to_menu(self.github_icon, f"Star {self.github_stars}", "https://github.com/emy69/CoomerDL")
        self.add_icon_to_menu(self.discord_icon, "Discord", "https://discord.gg/ku8gSPsesh")
        self.add_icon_to_menu(self.new_icon, "Support", "https://buymeacoffee.com/emy_69")
        
        # Inicializar variables para menús desplegables
        self.archivo_menu_frame = None
        self.ayuda_menu_frame = None
        self.donaciones_menu_frame = None
    
    def add_menu_button(self, text: str, command):
        """
        Añade un botón a la barra de menú.
        """
        button = ctk.CTkButton(
            self.menu_bar,
            text=self.tr(text),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=command
        )
        button.pack(side="left")
        button.bind("<Button-1>", lambda e: "break")
    
    def add_icon_to_menu(self, icon: Optional[ctk.CTkImage], text: str, link: str):
        """
        Añade un icono con texto a la barra de menú.
        """
        if icon:
            frame = ctk.CTkFrame(self.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            frame.pack(side="right", padx=5)
            label = ctk.CTkLabel(
                frame,
                image=icon,
                text=text,
                compound="left"
            )
            label.pack(padx=5, pady=5)
            frame.bind("<Enter>", lambda e: frame.configure(fg_color="gray25"))
            frame.bind("<Leave>", lambda e: frame.configure(fg_color="transparent"))
            label.bind("<Enter>", lambda e: frame.configure(fg_color="gray25"))
            label.bind("<Leave>", lambda e: frame.configure(fg_color="transparent"))
            label.bind("<Button-1>", lambda e: webbrowser.open(link))
    
    def create_input_frame(self):
        """
        Crea el marco de entrada para la URL y la carpeta de descarga.
        """
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
        
        self.folder_path = ctk.CTkLabel(self.input_frame, text="", cursor="hand2", font=("Arial", 13))
        self.folder_path.grid(row=2, column=0, columnspan=2, sticky='w')
        self.folder_path.bind("<Button-1>", self.open_download_folder)
        self.folder_path.bind("<Enter>", self.on_hover_enter)
        self.folder_path.bind("<Leave>", self.on_hover_leave)
    
    def create_options_frame(self):
        """
        Crea el marco de opciones para seleccionar tipos de descarga.
        """
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, fill='x', padx=20)
        
        self.download_images_check = self.create_checkbox(self.options_frame, self.tr("Descargar Imágenes"), default=True)
        self.download_videos_check = self.create_checkbox(self.options_frame, self.tr("Descargar Vídeos"), default=True)
        self.download_compressed_check = self.create_checkbox(self.options_frame, self.tr("Descargar Comprimidos"), default=True)
    
    def create_checkbox(self, parent, text: str, default: bool = False) -> ctk.CTkCheckBox:
        """
        Crea una casilla de verificación.
        """
        checkbox = ctk.CTkCheckBox(parent, text=text)
        checkbox.pack(side='left', padx=10)
        if default:
            checkbox.select()
        return checkbox
    
    def create_action_frame(self):
        """
        Crea el marco de acciones para descargar y cancelar.
        """
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.pack(pady=10, fill='x', padx=20)
        
        self.download_button = ctk.CTkButton(self.action_frame, text=self.tr("Descargar"), command=self.start_download)
        self.download_button.pack(side='left', padx=10)
        
        self.cancel_button = ctk.CTkButton(self.action_frame, text=self.tr("Cancelar Descarga"), state="disabled", command=self.cancel_download)
        self.cancel_button.pack(side='left', padx=10)
        
        self.progress_label = ctk.CTkLabel(self.action_frame, text="")
        self.progress_label.pack(side='left', padx=10)
        
        self.download_all_check = ctk.CTkCheckBox(self.action_frame)
        self.download_all_check.pack(side='left', padx=10)
        self.download_all_check.configure(command=self.update_info_text)
        
        self.update_info_text()
    
    def create_log_textbox(self):
        """
        Crea el cuadro de texto para mostrar los logs.
        """
        self.log_textbox = ctk.CTkTextbox(self, width=590, height=200, state='disabled')
        self.log_textbox.pack(pady=(10, 0), padx=20, fill='both', expand=True)
    
    def create_progress_frame(self):
        """
        Crea el marco para la barra de progreso.
        """
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.pack(pady=(0, 10), fill='x', padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        self.progress_percentage = ctk.CTkLabel(self.progress_frame, text="0%")
        self.progress_percentage.pack(side='left')
        
        # Icono de descarga
        self.download_icon = self.load_and_resize_image('resources/img/download_icon.png', (24, 24))
        
        self.toggle_details_button = ctk.CTkLabel(self.progress_frame, image=self.download_icon, text="", cursor="hand2")
        self.toggle_details_button.pack(side='left', padx=(5, 0))
        self.toggle_details_button.bind("<Button-1>", lambda e: self.toggle_progress_details())
        self.toggle_details_button.bind("<Enter>", lambda e: self.toggle_details_button.configure(fg_color="gray25"))
        self.toggle_details_button.bind("<Leave>", lambda e: self.toggle_details_button.configure(fg_color="transparent"))
        
        self.progress_details_frame = ctk.CTkFrame(self)
        self.progress_details_frame.place_forget()
    
    def create_footer(self):
        """
        Crea el pie de página para mostrar velocidad y ETA.
        """
        footer = ctk.CTkFrame(self, height=30, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        
        self.footer_eta_label = ctk.CTkLabel(footer, text="", font=("Arial", 10))
        self.footer_eta_label.pack(side="left", padx=20)
        
        self.footer_speed_label = ctk.CTkLabel(footer, text="", font=("Arial", 10))
        self.footer_speed_label.pack(side="right", padx=20)
    
    def create_context_menu(self):
        """
        Crea el menú contextual para la entrada de URL.
        """
        self.context_menu = tk.Menu(self.url_entry, tearoff=0)
        self.context_menu.add_command(label=self.tr("Copiar"), command=self.copy_to_clipboard)
        self.context_menu.add_command(label=self.tr("Pegar"), command=self.paste_from_clipboard)
        self.context_menu.add_command(label=self.tr("Cortar"), command=self.cut_to_clipboard)
        
        self.url_entry.bind("<Button-3>", self.show_context_menu)
        self.bind("<Button-1>", self.on_click)
    
    def update_ui_texts(self):
        """
        Actualiza los textos de la interfaz según el idioma seleccionado.
        """
        # Actualizar textos de los botones del menú
        for widget in self.menu_bar.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                text = widget.cget("text").strip()
                if text in ["Archivo", "Ayuda", "Donaciones"]:
                    widget.configure(text=self.tr(text))
        
        # Actualizar otros textos
        self.url_label.configure(text=self.tr("URL de la página web:"))
        self.browse_button.configure(text=self.tr("Seleccionar Carpeta"))
        self.download_images_check.configure(text=self.tr("Descargar Imágenes"))
        self.download_videos_check.configure(text=self.tr("Descargar Vídeos"))
        self.download_compressed_check.configure(text=self.tr("Descargar Comprimidos"))
        self.download_button.configure(text=self.tr("Descargar"))
        self.cancel_button.configure(text=self.tr("Cancelar Descarga"))
        self.title(self.tr(f"Downloader [{VERSION}]"))
        
        # Actualizar tooltip de información
        if hasattr(self, 'info_label'):
            self.create_tooltip(self.info_label, self.tr(
                "Selecciona esta opción para descargar todo el contenido disponible del perfil,\n"
                "en lugar de solo los posts del URL proporcionado."
            ))
        
        self.update_info_text()
    
    def toggle_archivo_menu(self):
        """
        Muestra u oculta el menú de archivo.
        """
        if self.archivo_menu_frame and self.archivo_menu_frame.winfo_exists():
            self.archivo_menu_frame.destroy()
        else:
            self.close_all_menus()
            self.archivo_menu_frame = self.create_menu_frame([
                (self.tr("Configuraciones"), self.settings_window.open_settings),
                ("separator", None),
                (self.tr("Salir"), self.quit),
            ], x=0)
    
    def create_menu_frame(self, options, x: int) -> ctk.CTkFrame:
        """
        Crea un marco de menú con las opciones proporcionadas.
        """
        menu_frame = ctk.CTkFrame(self, corner_radius=5, fg_color="gray25", border_color="black", border_width=1)
        menu_frame.place(x=x, y=30)
        menu_frame.bind("<Button-1>", lambda e: "break")
        
        for option in options:
            if option[0] == "separator":
                separator = ctk.CTkFrame(menu_frame, height=1, fg_color="gray50")
                separator.pack(fill="x", padx=5, pady=5)
                separator.bind("<Button-1>", lambda e: "break")
            elif option[1] is None:
                label = ctk.CTkLabel(menu_frame, text=option[0], anchor="w", fg_color="gray30")
                label.pack(fill="x", padx=5, pady=2)
                label.bind("<Button-1>", lambda e: "break")
            else:
                btn = ctk.CTkButton(
                    menu_frame,
                    text=option[0],
                    fg_color="transparent",
                    hover_color="gray35",
                    anchor="w",
                    text_color="white",
                    command=option[1]
                )
                btn.pack(fill="x", padx=5, pady=2)
                btn.bind("<Button-1>", lambda e: "break")
        
        return menu_frame
    
    def close_all_menus(self):
        """
        Cierra todos los menús desplegables abiertos.
        """
        for menu_frame in [self.archivo_menu_frame, self.ayuda_menu_frame, self.donaciones_menu_frame]:
            if menu_frame and menu_frame.winfo_exists():
                menu_frame.destroy()
    
    def load_and_resize_image(self, path: str, size: Tuple[int, int]) -> ctk.CTkImage:
        """
        Carga y redimensiona una imagen.
        """
        img = Image.open(path)
        return ctk.CTkImage(img, size=size)
    
    def load_icon(self, icon_path: str, icon_name: str, size: Tuple[int, int] = (16, 16)) -> Optional[ctk.CTkImage]:
        """
        Carga un icono y maneja errores si no se puede cargar.
        """
        try:
            return self.load_and_resize_image(icon_path, size)
        except Exception as e:
            self.add_log_message_safe(f"Error al cargar el icono {icon_name}: {e}")
            return None
    
    def on_app_close(self):
        """
        Maneja el evento de cierre de la aplicación.
        """
        if self.is_download_active() and not self.active_downloader.cancel_requested:
            messagebox.showwarning(
                self.tr("Descarga Activa"),
                self.tr("Hay una descarga en progreso. Por favor, cancela la descarga antes de cerrar.")
            )
        else:
            self.destroy()
    
    def is_download_active(self) -> bool:
        """
        Verifica si hay una descarga activa.
        """
        return self.active_downloader is not None
    
    def close_program(self):
        """
        Cierra todas las ventanas y termina el proceso principal.
        """
        self.destroy()
        current_process = psutil.Process(os.getpid())
        for handler in current_process.children(recursive=True):
            handler.kill()
        current_process.kill()
    
    def save_language_preference(self, language_code: str):
        """
        Guarda la preferencia de idioma.
        """
        config = {'language': language_code}
        with open('resources/config/languages/save_language/language_config.json', 'w', encoding='utf-8') as config_file:
            json.dump(config, config_file)
        self.load_translations(language_code)
        self.update_ui_texts()
    
    def load_language_preference(self) -> str:
        """
        Carga la preferencia de idioma.
        """
        try:
            with open('resources/config/languages/save_language/language_config.json', 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
                return config.get('language', 'en')
        except FileNotFoundError:
            return 'en'
    
    def load_translations(self, lang: str):
        """
        Carga las traducciones para el idioma seleccionado.
        """
        path = "resources/config/languages/translations.json"
        with open(path, 'r', encoding='utf-8') as file:
            all_translations = json.load(file)
            self.translations = {key: value.get(lang, key) for key, value in all_translations.items()}
    
    def tr(self, text: str, **kwargs) -> str:
        """
        Devuelve el texto traducido.
        """
        translated_text = self.translations.get(text, text)
        if kwargs:
            translated_text = translated_text.format(**kwargs)
        return translated_text
    
    def select_folder(self):
        """
        Abre un diálogo para seleccionar la carpeta de descarga.
        """
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.download_folder = folder_selected
            self.folder_path.configure(text=folder_selected)
            self.save_download_folder(folder_selected)
    
    def load_download_folder(self) -> Optional[str]:
        """
        Carga la carpeta de descarga desde la configuración.
        """
        config_path = 'resources/config/download_path/download_folder.json'
        config_dir = Path(config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        if not Path(config_path).exists():
            with open(config_path, 'w', encoding='utf-8') as config_file:
                json.dump({'download_folder': ''}, config_file)
        try:
            with open(config_path, 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
                return config.get('download_folder', '')
        except json.JSONDecodeError:
            return ''
    
    def save_download_folder(self, folder_path: str):
        """
        Guarda la carpeta de descarga en la configuración.
        """
        config = {'download_folder': folder_path}
        with open('resources/config/download_path/download_folder.json', 'w', encoding='utf-8') as config_file:
            json.dump(config, config_file)
    
    def load_github_icon(self) -> Optional[ctk.CTkImage]:
        """
        Carga el icono de GitHub.
        """
        return self.load_icon("resources/img/github-logo-24.png", "GitHub")
    
    def load_discord_icon(self) -> Optional[ctk.CTkImage]:
        """
        Carga el icono de Discord.
        """
        return self.load_icon("resources/img/discord-alt-logo-24.png", "Discord")
    
    def load_new_icon(self) -> Optional[ctk.CTkImage]:
        """
        Carga el nuevo icono de soporte.
        """
        return self.load_icon("resources/img/dollar-circle-solid-24.png", "New Icon")
    
    def update_info_text(self):
        """
        Actualiza el texto de la casilla de descarga completa.
        """
        text = self.tr("Descargar todo el perfil") if self.download_all_check.get() else self.tr("Descargar solo los posts del URL proporcionado")
        self.download_all_check.configure(text=text)
        
        # Añadir icono de información si no existe
        if not hasattr(self, 'info_label'):
            info_icon = self.load_and_resize_image('resources/img/info_icon.png', (16, 16))
            self.info_label = ctk.CTkLabel(self.action_frame, image=info_icon, text="", cursor="hand2")
            self.info_label.pack(side='left', padx=5)
            self.create_tooltip(self.info_label, self.tr(
                "Selecciona esta opción para descargar todo el contenido disponible del perfil,\n"
                "en lugar de solo los posts del URL proporcionado."
            ))
    
    def create_tooltip(self, widget: tk.Widget, text: str):
        """
        Crea un tooltip para un widget.
        """
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.withdraw()
        
        tooltip_frame = tk.Frame(tooltip, bg="#333333", relief='solid', bd=1, padx=10, pady=10)
        tooltip_label = tk.Label(tooltip_frame, text=text, bg="#333333", fg="white", font=("Arial", 10), justify="left")
        tooltip_label.pack()
        tooltip_frame.pack()
        
        def enter(event):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tooltip.wm_geometry(f"+{x}+{y}")
            tooltip.deiconify()
        
        def leave(event):
            tooltip.withdraw()
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def toggle_progress_details(self):
        """
        Alterna la visibilidad de los detalles de progreso.
        """
        self.progress_manager.toggle_progress_details()
    
    def center_progress_details_frame(self):
        """
        Centra el marco de detalles de progreso.
        """
        self.progress_manager.center_progress_details_frame()
    
    def add_log_message_safe(self, message: str):
        """
        Añade un mensaje de log de forma segura desde hilos.
        """
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
        """
        Limita el número de líneas en el cuadro de logs.
        """
        log_lines = self.log_textbox.get("1.0", "end-1c").split("\n")
        if len(log_lines) > MAX_LOG_LINES:
            self.log_textbox.configure(state='normal')
            self.log_textbox.delete("1.0", f"{len(log_lines) - MAX_LOG_LINES}.0")
            self.log_textbox.configure(state='disabled')
    
    def export_logs(self):
        """
        Exporta los logs a un archivo.
        """
        log_folder = "resources/config/logs/"
        Path(log_folder).mkdir(parents=True, exist_ok=True)
        log_file_path = Path(log_folder) / f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            total_files = self.active_downloader.total_files if self.active_downloader else 0
            completed_files = self.active_downloader.completed_files if self.active_downloader else 0
            skipped_files = self.active_downloader.skipped_files if self.active_downloader else []
            failed_files = self.active_downloader.failed_files if self.active_downloader else []
            
            total_images = completed_files if self.download_images_check.get() else 0
            total_videos = completed_files if self.download_videos_check.get() else 0
            errors = len(self.errors)
            warnings = len(self.warnings)
            duration = datetime.datetime.now() - self.download_start_time if self.download_start_time else "N/A"
            
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
            
            with open(log_file_path, 'w', encoding='utf-8') as file:
                file.write(summary)
                file.write(self.log_textbox.get("1.0", tk.END))
            self.add_log_message_safe(self.tr("Logs exportados exitosamente a {path}", path=log_file_path))
        except Exception as e:
            self.add_log_message_safe(self.tr("No se pudo exportar los logs: {e}", e=e))
    
    def copy_to_clipboard(self):
        """
        Copia el texto seleccionado al portapapeles.
        """
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
        """
        Pega el texto del portapapeles en la entrada de URL.
        """
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                try:
                    self.url_entry.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                self.url_entry.insert(tk.INSERT, clipboard_text)
            else:
                self.add_log_message_safe(self.tr("No hay texto en el portapapeles para pegar."))
        except tk.TclError as e:
            self.add_log_message_safe(self.tr(f"Error al pegar desde el portapapeles: {e}"))
    
    def cut_to_clipboard(self):
        """
        Corta el texto seleccionado y lo copia al portapapeles.
        """
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
    
    def show_context_menu(self, event):
        """
        Muestra el menú contextual.
        """
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.context_menu.grab_release()
    
    def check_update_queue(self):
        """
        Revisa y ejecuta las tareas en la cola de actualización.
        """
        while not self.update_queue.empty():
            task = self.update_queue.get_nowait()
            task()
        self.after(100, self.check_update_queue)
    
    def enable_widgets(self):
        """
        Habilita los widgets después de una operación.
        """
        self.update_queue.put(lambda: self.download_button.configure(state="normal"))
        self.update_queue.put(lambda: self.cancel_button.configure(state="disabled"))
        self.update_queue.put(lambda: self.download_all_check.configure(state="normal"))
    
    def update_max_downloads(self, max_downloads: int):
        """
        Actualiza el número máximo de descargas simultáneas.
        """
        self.max_downloads = max_downloads
        for downloader in [getattr(self, attr, None) for attr in ['general_downloader', 'erome_downloader', 'bunkr_downloader']]:
            if downloader:
                downloader.max_workers = max_downloads
    
    def on_hover_enter(self, event):
        """
        Aplica efecto hover al entrar sobre la etiqueta de carpeta.
        """
        self.folder_path.configure(font=("Arial", 13, "underline"))
    
    def on_hover_leave(self, event):
        """
        Quita el efecto hover al salir de la etiqueta de carpeta.
        """
        self.folder_path.configure(font=("Arial", 13))
    
    def open_download_folder(self, event=None):
        """
        Abre la carpeta de descarga en el explorador de archivos.
        """
        if self.download_folder and os.path.exists(self.download_folder):
            try:
                if sys.platform == "win32":
                    os.startfile(self.download_folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", self.download_folder])
                else:
                    subprocess.Popen(["xdg-open", self.download_folder])
            except Exception as e:
                self.add_log_message_safe(self.tr("Error al abrir la carpeta: {e}", e=e))
        else:
            messagebox.showerror(self.tr("Error"), self.tr("La carpeta no existe o no es válida."))
    
    def on_click(self, event):
        """
        Cierra los menús desplegables si se hace clic fuera de ellos.
        """
        widgets_to_ignore = [self.menu_bar]
        for frame in [self.archivo_menu_frame, self.ayuda_menu_frame, self.donaciones_menu_frame]:
            if frame and frame.winfo_exists():
                widgets_to_ignore.append(frame)
                widgets_to_ignore.extend(self.get_all_children(frame))
        if event.widget not in widgets_to_ignore:
            self.close_all_menus()
    
    def get_all_children(self, widget: tk.Widget) -> list:
        """
        Obtiene todos los hijos de un widget de forma recursiva.
        """
        children = widget.winfo_children()
        all_children = list(children)
        for child in children:
            all_children.extend(self.get_all_children(child))
        return all_children
    
    def start_download(self):
        """
        Inicia el proceso de descarga basado en la URL proporcionada.
        """
        url = self.url_entry.get().strip()
        if not self.download_folder:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, selecciona una carpeta de descarga."))
            return
        
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.download_start_time = datetime.datetime.now()
        self.errors = []
        download_all = self.download_all_check.get()
        
        parsed_url = urlparse(url)
        
        if "erome.com" in url:
            self.handle_erome_download(url)
        elif re.search(r"https?://([a-z0-9-]+\.)?bunkr\.[a-z]{2,}", url):
            self.handle_bunkr_download(url)
        elif parsed_url.netloc in ["coomer.su", "kemono.su"]:
            self.handle_general_download(parsed_url, download_all)
        elif "simpcity.su" in url:
            self.handle_simpcity_download(url)
        elif "jpg5.su" in url:
            self.handle_jpg5_download()
        else:
            self.add_log_message_safe(self.tr("URL no válida"))
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
    
    def handle_erome_download(self, url: str):
        """
        Maneja la descarga desde Erome.
        """
        self.add_log_message_safe(self.tr("Descargando Erome"))
        is_profile_download = "/a/" not in url
        self.setup_erome_downloader(is_profile_download=is_profile_download)
        self.active_downloader = self.erome_downloader
        if "/a/" in url:
            self.add_log_message_safe(self.tr("URL del álbum"))
            target = self.active_downloader.process_album_page
            args = (url, self.download_folder, self.download_images_check.get(), self.download_videos_check.get())
        else:
            self.add_log_message_safe(self.tr("URL del perfil"))
            target = self.active_downloader.process_profile_page
            args = (url, self.download_folder, self.download_images_check.get(), self.download_videos_check.get())
        self.start_download_thread(target, args)
    
    def handle_bunkr_download(self, url: str):
        """
        Maneja la descarga desde Bunkr.
        """
        self.add_log_message_safe(self.tr("Descargando Bunkr"))
        self.setup_bunkr_downloader()
        self.active_downloader = self.bunkr_downloader
        if "/v/" in url or "/i/" in url:
            self.add_log_message_safe(self.tr("URL del post"))
            target = self.active_downloader.descargar_post_bunkr
            args = (url,)
        else:
            self.add_log_message_safe(self.tr("URL del perfil"))
            target = self.active_downloader.descargar_perfil_bunkr
            args = (url,)
        self.start_download_thread(target, args)
    
    def handle_general_download(self, parsed_url: ParseResult, download_all: bool):
        """
        Maneja la descarga desde sitios generales como coomer.su o kemono.su.
        """
        self.add_log_message_safe(self.tr("Iniciando descarga..."))
        self.setup_general_downloader()
        self.active_downloader = self.general_downloader
        
        site = parsed_url.netloc
        service, user, post = extract_ck_parameters(parsed_url)
        if not service or not user:
            error_msg = self.tr("No se pudo extraer los parámetros necesarios del URL.")
            self.add_log_message_safe(error_msg)
            messagebox.showerror(self.tr("Error"), error_msg)
            self.reset_download_buttons()
            return
        
        self.add_log_message_safe(self.tr("Servicio extraído: {service} del sitio: {site}", service=service, site=site))
        
        if post:
            self.add_log_message_safe(self.tr("Descargando post único..."))
            target = self.start_ck_post_download
            args = (site, service, user, post)
        else:
            query, offset = extract_ck_query(parsed_url)
            self.add_log_message_safe(self.tr("Descargando todo el contenido del usuario..." if download_all else "Descargando solo los posts del URL proporcionado..."))
            target = self.start_ck_profile_download
            args = (site, service, user, query, download_all, offset)
        
        self.start_download_thread(target, args)
    
    def handle_simpcity_download(self, url: str):
        """
        Maneja la descarga desde SimpCity.
        """
        self.add_log_message_safe(self.tr("Descargando SimpCity"))
        self.setup_simpcity_downloader()
        self.active_downloader = self.simpcity_downloader
        target = self.active_downloader.download_images_from_simpcity
        args = (url,)
        self.start_download_thread(target, args)
    
    def handle_jpg5_download(self):
        """
        Maneja la descarga desde Jpg5.
        """
        self.add_log_message_safe(self.tr("Descargando desde Jpg5"))
        self.setup_jpg5_downloader()
        self.active_downloader = self.jpg5_downloader
        target = self.active_downloader.descargar_imagenes
        args = ()
        self.start_download_thread(target, args)
    
    def start_download_thread(self, target, args):
        """
        Inicia un hilo de descarga.
        """
        download_thread = threading.Thread(target=self.wrapped_download, args=(target, *args))
        download_thread.start()
    
    def wrapped_download(self, download_method, *args):
        """
        Envuélve el método de descarga para manejar la finalización.
        """
        try:
            download_method(*args)
        finally:
            self.active_downloader = None
            self.enable_widgets()
            self.export_logs()
    
    def start_ck_profile_download(self, site: str, service: str, user: str, query: Optional[str], download_all: bool, initial_offset: int):
        """
        Inicia la descarga de un perfil completo.
        """
        download_info = self.active_downloader.download_media(site, user, service, query=query, download_all=download_all, initial_offset=initial_offset)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
    
    def start_ck_post_download(self, site: str, service: str, user: str, post: str):
        """
        Inicia la descarga de un post único.
        """
        download_info = self.active_downloader.download_single_post(site, post, service, user)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
    
    def cancel_download(self):
        """
        Cancela la descarga activa.
        """
        if self.active_downloader:
            self.active_downloader.request_cancel()
            self.active_downloader = None
            self.clear_progress_bars()
        else:
            self.add_log_message_safe(self.tr("No hay una descarga en curso para cancelar."))
        self.enable_widgets()
    
    def clear_progress_bars(self):
        """
        Limpia todas las barras de progreso.
        """
        for file_id in list(self.progress_bars.keys()):
            self.remove_progress_bar(file_id)
    
    def show_context_menu(self, event):
        """
        Muestra el menú contextual.
        """
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.context_menu.grab_release()
    
    # Métodos para configurar los distintos descargadores
    def setup_erome_downloader(self, is_profile_download: bool):
        """
        Configura el descargador de Erome.
        """
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
    
    def setup_simpcity_downloader(self):
        """
        Configura el descargador de SimpCity.
        """
        self.simpcity_downloader = SimpCity(
            download_folder=self.download_folder,
            log_callback=self.add_log_message_safe,
            enable_widgets_callback=self.enable_widgets,
            update_progress_callback=self.update_progress,
            update_global_progress_callback=self.update_global_progress,
            tr=self.tr
        )
    
    def setup_bunkr_downloader(self):
        """
        Configura el descargador de Bunkr.
        """
        self.bunkr_downloader = BunkrDownloader(
            download_folder=self.download_folder,
            log_callback=self.add_log_message_safe,
            enable_widgets_callback=self.enable_widgets,
            update_progress_callback=self.update_progress,
            update_global_progress_callback=self.update_global_progress,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Referer': 'https://bunkr.site/',
            },
            max_workers=self.max_downloads
        )
    
    def setup_general_downloader(self):
        """
        Configura el descargador general para coomer.su y kemono.su.
        """
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
    
    def setup_jpg5_downloader(self):
        """
        Configura el descargador de Jpg5.
        """
        self.jpg5_downloader = Jpg5Downloader(
            url=self.url_entry.get().strip(),
            carpeta_destino=self.download_folder,
            log_callback=self.add_log_message_safe,
            tr=self.tr,
            progress_manager=self.progress_manager,
            max_workers=self.max_downloads
        )
    
    # Métodos relacionados con el progreso
    def update_progress(self, downloaded: int, total: int, file_id: Optional[str] = None, file_path: Optional[str] = None, speed: Optional[str] = None, eta: Optional[str] = None):
        """
        Actualiza el progreso de descarga.
        """
        self.progress_manager.update_progress(downloaded, total, file_id, file_path, speed, eta)
    
    def remove_progress_bar(self, file_id: str):
        """
        Elimina una barra de progreso específica.
        """
        self.progress_manager.remove_progress_bar(file_id)
    
    def update_global_progress(self, completed_files: int, total_files: int):
        """
        Actualiza el progreso global de las descargas.
        """
        self.progress_manager.update_global_progress(completed_files, total_files)
    
    # Métodos de traducción y localización
    def tr(self, text: str, **kwargs) -> str:
        """
        Traduce el texto dado utilizando las traducciones cargadas.
        """
        translated_text = self.translations.get(text, text)
        if kwargs:
            translated_text = translated_text.format(**kwargs)
        return translated_text
    
    # Métodos de gestión de menús y eventos
    def toggle_progress_details(self):
        """
        Alterna la visibilidad de los detalles de progreso.
        """
        self.progress_manager.toggle_progress_details()
    
    def center_progress_details_frame(self):
        """
        Centra el marco de detalles de progreso.
        """
        self.progress_manager.center_progress_details_frame()
    
    # Métodos para manejar la descarga
    def start_download(self):
        """
        Inicia el proceso de descarga basado en la URL proporcionada.
        """
        url = self.url_entry.get().strip()
        if not self.download_folder:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, selecciona una carpeta de descarga."))
            return
        
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.download_start_time = datetime.datetime.now()
        self.errors = []
        download_all = self.download_all_check.get()
        
        parsed_url = urlparse(url)
        
        if "erome.com" in url:
            self.handle_erome_download(url)
        elif re.search(r"https?://([a-z0-9-]+\.)?bunkr\.[a-z]{2,}", url):
            self.handle_bunkr_download(url)
        elif parsed_url.netloc in ["coomer.su", "kemono.su"]:
            self.handle_general_download(parsed_url, download_all)
        elif "simpcity.su" in url:
            self.handle_simpcity_download(url)
        elif "jpg5.su" in url:
            self.handle_jpg5_download()
        else:
            self.add_log_message_safe(self.tr("URL no válida"))
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
    
    def start_ck_profile_download(self, site: str, service: str, user: str, query: Optional[str], download_all: bool, initial_offset: int):
        """
        Inicia la descarga de un perfil completo.
        """
        download_info = self.active_downloader.download_media(site, user, service, query=query, download_all=download_all, initial_offset=initial_offset)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
    
    def start_ck_post_download(self, site: str, service: str, user: str, post: str):
        """
        Inicia la descarga de un post único.
        """
        download_info = self.active_downloader.download_single_post(site, post, service, user)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
    
    def wrapped_download(self, download_method, *args):
        """
        Envuélve el método de descarga para manejar la finalización.
        """
        try:
            download_method(*args)
        finally:
            self.active_downloader = None
            self.enable_widgets()
            self.export_logs()
    
    # Métodos para manejar los menús contextuales y eventos
    def on_click(self, event):
        """
        Cierra los menús desplegables si se hace clic fuera de ellos.
        """
        widgets_to_ignore = [self.menu_bar]
        for frame in [self.archivo_menu_frame, self.ayuda_menu_frame, self.donaciones_menu_frame]:
            if frame and frame.winfo_exists():
                widgets_to_ignore.append(frame)
                widgets_to_ignore.extend(self.get_all_children(frame))
        if event.widget not in widgets_to_ignore:
            self.close_all_menus()
    
    def get_all_children(self, widget: tk.Widget) -> list:
        """
        Obtiene todos los hijos de un widget de forma recursiva.
        """
        children = widget.winfo_children()
        all_children = list(children)
        for child in children:
            all_children.extend(self.get_all_children(child))
        return all_children
    
    # Métodos para manejar la cola de actualización
    def check_update_queue(self):
        """
        Revisa y ejecuta las tareas en la cola de actualización.
        """
        while not self.update_queue.empty():
            task = self.update_queue.get_nowait()
            task()
        self.after(100, self.check_update_queue)
    
    def enable_widgets(self):
        """
        Habilita los widgets después de una operación.
        """
        self.update_queue.put(lambda: self.download_button.configure(state="normal"))
        self.update_queue.put(lambda: self.cancel_button.configure(state="disabled"))
        self.update_queue.put(lambda: self.download_all_check.configure(state="normal"))
    
    # Métodos de manejo de errores y logs
    def log_error(self, error_message: str):
        """
        Registra un error.
        """
        self.errors.append(error_message)
        self.add_log_message_safe(f"Error: {error_message}")
    
    def log_warning(self, warning_message: str):
        """
        Registra una advertencia.
        """
        self.warnings.append(warning_message)
        self.add_log_message_safe(f"Warning: {warning_message}")
    
    # Métodos de carga de iconos
    def load_github_icon(self) -> Optional[ctk.CTkImage]:
        """
        Carga el icono de GitHub.
        """
        return self.load_icon("resources/img/github-logo-24.png", "GitHub")
    
    def load_discord_icon(self) -> Optional[ctk.CTkImage]:
        """
        Carga el icono de Discord.
        """
        return self.load_icon("resources/img/discord-alt-logo-24.png", "Discord")
    
    def load_new_icon(self) -> Optional[ctk.CTkImage]:
        """
        Carga el nuevo icono de soporte.
        """
        return self.load_icon("resources/img/dollar-circle-solid-24.png", "New Icon")
