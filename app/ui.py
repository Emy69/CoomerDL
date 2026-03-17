import datetime
import functools
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional
from urllib.parse import ParseResult, parse_qs, urlparse

import customtkinter as ctk
import psutil
import requests
from PIL import Image, ImageTk

from app.about_window import AboutWindow
from app.donors import DonorsModal
from app.progress_manager import ProgressManager
from app.settings_window import SettingsWindow
from app.models.app_state import AppState
from app.services.settings_service import SettingsService
from app.services.translation_service import TranslationService

from downloader.bunkr import BunkrDownloader
from downloader.downloader import Downloader
from downloader.erome import EromeDownloader
from downloader.jpg5 import Jpg5Downloader
from downloader.simpcity import SimpCity
from app.adapters.downloader_factory import DownloaderFactory

VERSION = "V0.8.12"
MAX_LOG_LINES = None


def extract_ck_parameters(url: ParseResult) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get the service, user and post id from the url if they exist.
    Returns: service, user, post
    """
    match = re.search(r"/(?P<service>[^/?]+)(/user/(?P<user>[^/?]+)(/post/(?P<post>[^/?]+))?)?", url.path)
    if match:
        service, user, post = match.group("service", "user", "post")
        return service, user, post
    return None, None, None


def extract_ck_query(url: ParseResult) -> tuple[Optional[str], int]:
    """
    Try to obtain the query and offset from the url if they exist.
    """
    query = parse_qs(url.query)
    q = query.get("q")[0] if query.get("q") and len(query.get("q")) > 0 else "0"
    o = query.get("o")[0] if query.get("o") and len(query.get("o")) > 0 else "0"
    return q, int(o) if str(o).isdigit() else 0


class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        super().__init__()

        self.version = VERSION
        self.title(f"Downloader [{VERSION}]")

        # ---------------------------
        # Estado y servicios
        # ---------------------------
        self.app_state = AppState()
        self.settings_service = SettingsService()
        self.app_state.language = self.settings_service.load_language_preference("en")
        self.app_state.download_folder = self.settings_service.load_download_folder("downloads")
        self.translation_service = TranslationService(language=self.app_state.language)
        self.downloader_factory = DownloaderFactory(self)
        # Compatibilidad temporal con código existente
        self.download_folder = self.app_state.download_folder

        # Estado runtime
        self.errors = []
        self.warnings = []
        self.all_logs = []
        self._log_buffer = []
        self.github_stars = 0
        self.image_downloader = None
        self.progress_bars = {}
        self.active_downloader = None
        self.download_start_time = None
        self.extras_window = None
        self.latest_release_url = None

        self.update_queue = queue.Queue()
        self.autoscroll_logs_var = tk.BooleanVar(value=False)

        # Setup ventana
        self.setup_window()

        # Settings window
        self.settings_window = SettingsWindow(
            self,
            self.tr,
            self.load_translations,
            self.update_ui_texts,
            self.save_language_preference,
            VERSION,
            None,
            self.check_for_new_version,
            on_settings_changed=self.apply_runtime_settings
        )

        # Cargar settings del settings window
        self.settings = self.settings_window.load_settings()

        # Ventanas auxiliares
        self.about_window = AboutWindow(self, self.tr, VERSION)

        # GitHub info
        self.github_stars = self.get_github_stars("emy69", "CoomerDL")
        self.github_icon = self.load_github_icon()

        # Inicializar UI
        self.initialize_ui()
        self.update_ui_texts()

        # Aplicar carpeta cargada al label
        if self.download_folder:
            self.folder_path.configure(text=self.download_folder)

        # Crear downloader por defecto para ajustes runtime
        self._create_default_downloader()

        # Cargar iconos
        self.icons = {
            "image": self.load_and_resize_image("resources/img/iconos/ui/image_icon.png", (40, 40)),
            "video": self.load_and_resize_image("resources/img/iconos/ui/video.png", (40, 40)),
            "zip": self.load_and_resize_image("resources/img/iconos/ui/file-zip.png", (40, 40)),
            "default": self.load_and_resize_image("resources/img/iconos/ui/default_icon.png", (40, 40)),
        }

        # Progress manager
        self.progress_manager = ProgressManager(
            root=self,
            icons=self.icons,
            footer_speed_label=self.footer_speed_label,
            footer_eta_label=self.footer_eta_label,
            progress_bar=self.progress_bar,
            progress_percentage=self.progress_percentage
        )

        # Volcar logs bufferizados si hubo
        self.flush_log_buffer()

        # Queue / cierre
        self.check_update_queue()
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        # Check updates
        threading.Thread(target=self.check_for_new_version, args=(True,), daemon=True).start()

    # -------------------------------------------------------------------------
    # Wrappers de servicios para mantener compatibilidad con tu código actual
    # -------------------------------------------------------------------------
    def tr(self, key, **kwargs):
        return self.translation_service.tr(key, **kwargs)

    def load_translations(self, language=None):
        """
        Wrapper para mantener compatibilidad con SettingsWindow.
        """
        target_language = language or self.app_state.language
        self.app_state.language = target_language
        self.translation_service.set_language(target_language)

    def save_language_preference(self, language):
        """
        Wrapper para mantener compatibilidad con SettingsWindow.
        """
        self.app_state.language = language
        self.settings_service.save_language_preference(language)
        self.translation_service.set_language(language)

    def load_download_folder(self, default_folder="downloads"):
        self.app_state.download_folder = self.settings_service.load_download_folder(default_folder)
        self.download_folder = self.app_state.download_folder
        return self.download_folder

    def save_download_folder(self, folder):
        self.app_state.download_folder = folder
        self.download_folder = folder
        self.settings_service.save_download_folder(folder)

    # -------------------------------------------------------------------------
    # Setup base
    # -------------------------------------------------------------------------
    def setup_window(self):
        window_width, window_height = 1000, 600
        center_x = int((self.winfo_screenwidth() / 2) - (window_width / 2))
        center_y = int((self.winfo_screenheight() / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        if sys.platform == "win32":
            try:
                self.iconbitmap("resources/img/window.ico")
            except Exception:
                pass

    def _create_default_downloader(self):
        max_downloads = self.settings.get("max_downloads", 3)
        max_retries_setting = self.settings.get("max_retries", 3)
        retry_interval_setting = self.settings.get("retry_interval", 2.0)
        folder_structure_setting = self.settings.get("folder_structure", "default")

        self.max_downloads = max_downloads

        self.default_downloader = Downloader(
            download_folder=self.download_folder,
            max_workers=self.max_downloads,
            log_callback=self.add_log_message_safe,
            update_progress_callback=self.update_progress,
            update_global_progress_callback=self.update_global_progress,
            tr=self.tr,
            retry_interval=retry_interval_setting,
            folder_structure=folder_structure_setting,
            max_retries=max_retries_setting
        )

        self.settings_window.downloader = self.default_downloader

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------
    def initialize_ui(self):
        self.menu_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.menu_bar.pack(side="top", fill="x")

        self.create_custom_menubar()

        self.update_alert_frame = ctk.CTkFrame(self, fg_color="#4CAF50", corner_radius=0)
        self.update_alert_frame.pack(side="top", fill="x")
        self.update_alert_frame.pack_forget()

        self.update_alert_label = ctk.CTkLabel(
            self.update_alert_frame,
            text="",
            text_color="white",
            font=("Arial", 12, "bold")
        )
        self.update_alert_label.pack(side="left", padx=10, pady=5)

        self.update_download_button = ctk.CTkButton(
            self.update_alert_frame,
            text=self.tr("Download Now"),
            command=self.open_latest_release,
            fg_color="#388E3C",
            hover_color="#2E7D32"
        )
        self.update_download_button.pack(side="right", padx=10, pady=5)

        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill="x", padx=20, pady=20)
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_rowconfigure(1, weight=1)

        self.url_label = ctk.CTkLabel(self.input_frame, text=self.tr("URL de la página web:"))
        self.url_label.grid(row=0, column=0, sticky="w")

        self.url_entry = ctk.CTkEntry(self.input_frame)
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        self.browse_button = ctk.CTkButton(
            self.input_frame,
            text=self.tr("Seleccionar Carpeta"),
            command=self.select_folder
        )
        self.browse_button.grid(row=1, column=1, sticky="e")

        self.folder_path = ctk.CTkLabel(
            self.input_frame,
            text=self.download_folder or "",
            cursor="hand2",
            font=("Arial", 13)
        )
        self.folder_path.grid(row=2, column=0, columnspan=2, sticky="w")
        self.folder_path.bind("<Button-1>", self.open_download_folder)
        self.folder_path.bind("<Enter>", self.on_hover_enter)
        self.folder_path.bind("<Leave>", self.on_hover_leave)

        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, fill="x", padx=20)

        self.download_images_check = ctk.CTkCheckBox(self.options_frame, text=self.tr("Descargar Imágenes"))
        self.download_images_check.pack(side="left", padx=10)
        self.download_images_check.select()

        self.download_videos_check = ctk.CTkCheckBox(self.options_frame, text=self.tr("Descargar Vídeos"))
        self.download_videos_check.pack(side="left", padx=10)
        self.download_videos_check.select()

        self.download_compressed_check = ctk.CTkCheckBox(self.options_frame, text=self.tr("Descargar Comprimidos"))
        self.download_compressed_check.pack(side="left", padx=10)
        self.download_compressed_check.select()

        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.pack(pady=10, fill="x", padx=20)

        self.download_button = ctk.CTkButton(
            self.action_frame,
            text=self.tr("Descargar"),
            command=self.start_download
        )
        self.download_button.pack(side="left", padx=10)

        self.cancel_button = ctk.CTkButton(
            self.action_frame,
            text=self.tr("Cancelar Descarga"),
            state="disabled",
            command=self.cancel_download
        )
        self.cancel_button.pack(side="left", padx=10)

        self.autoscroll_logs_checkbox = ctk.CTkCheckBox(
            self.action_frame,
            text=self.tr("Auto-scroll logs"),
            variable=self.autoscroll_logs_var
        )
        self.autoscroll_logs_checkbox.pack(side="right")

        self.progress_label = ctk.CTkLabel(self.action_frame, text="")
        self.progress_label.pack(side="left", padx=10)

        self.log_textbox = ctk.CTkTextbox(self, width=590, height=200)
        self.log_textbox.pack(pady=(10, 0), padx=20, fill="both", expand=True)
        self.log_textbox.configure(state="disabled")

        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.pack(pady=(0, 10), fill="x", padx=20)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.progress_percentage = ctk.CTkLabel(self.progress_frame, text="0%")
        self.progress_percentage.pack(side="left")

        self.download_icon = self.load_and_resize_image("resources/img/iconos/ui/download_icon.png", (24, 24))
        self.toggle_details_button = ctk.CTkLabel(
            self.progress_frame,
            image=self.download_icon,
            text="",
            cursor="hand2"
        )
        self.toggle_details_button.pack(side="left", padx=(5, 0))
        self.toggle_details_button.bind("<Button-1>", lambda e: self.toggle_progress_details())
        self.toggle_details_button.bind("<Enter>", lambda e: self.toggle_details_button.configure(fg_color="gray25"))
        self.toggle_details_button.bind("<Leave>", lambda e: self.toggle_details_button.configure(fg_color="transparent"))

        self.progress_details_frame = ctk.CTkFrame(self)
        self.progress_details_frame.place_forget()

        self.context_menu = tk.Menu(self.url_entry, tearoff=0)
        self.context_menu.add_command(label=self.tr("Copiar"), command=self.copy_to_clipboard)
        self.context_menu.add_command(label=self.tr("Pegar"), command=self.paste_from_clipboard)
        self.context_menu.add_command(label=self.tr("Cortar"), command=self.cut_to_clipboard)

        self.url_entry.bind("<Button-3>", self.show_context_menu)
        self.bind("<Button-1>", self.on_click)

        footer = ctk.CTkFrame(self, height=30, corner_radius=0)
        footer.pack(side="bottom", fill="x")

        self.footer_eta_label = ctk.CTkLabel(footer, text="ETA: N/A", font=("Arial", 11))
        self.footer_eta_label.pack(side="left", padx=20)

        self.footer_speed_label = ctk.CTkLabel(footer, text="Speed: 0 KB/s", font=("Arial", 11))
        self.footer_speed_label.pack(side="right", padx=20)

    def update_ui_texts(self):
        for widget in self.menu_bar.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                text = widget.cget("text")
                if text.strip() in ["Archivo", "Ayuda", "Donaciones", "About", "Patreons"]:
                    widget.configure(text=self.tr(text.strip()))

        if hasattr(self, "archivo_menu_frame") and self.archivo_menu_frame and self.archivo_menu_frame.winfo_exists():
            self.archivo_menu_frame.destroy()
            self.toggle_archivo_menu()

        self.url_label.configure(text=self.tr("URL de la página web:"))
        self.browse_button.configure(text=self.tr("Seleccionar Carpeta"))
        self.download_images_check.configure(text=self.tr("Descargar Imágenes"))
        self.download_videos_check.configure(text=self.tr("Descargar Vídeos"))
        self.download_compressed_check.configure(text=self.tr("Descargar Comprimidos"))
        self.download_button.configure(text=self.tr("Descargar"))
        self.cancel_button.configure(text=self.tr("Cancelar Descarga"))
        self.autoscroll_logs_checkbox.configure(text=self.tr("Auto-scroll logs"))
        self.title(f"Downloader [{VERSION}]")
        self.update_download_button.configure(text=self.tr("Download Now"))

    # -------------------------------------------------------------------------
    # Eventos / UI auxiliar
    # -------------------------------------------------------------------------
    def on_app_close(self):
        if self.is_download_active() and not getattr(self.active_downloader, "cancel_requested", False):
            messagebox.showwarning(
                self.tr("Descarga Activa"),
                self.tr("Hay una descarga en progreso. Por favor, cancela la descarga antes de cerrar.")
            )
        else:
            self.destroy()

    def is_download_active(self):
        return self.active_downloader is not None

    def close_program(self):
        self.destroy()
        current_process = psutil.Process(os.getpid())
        for handler in current_process.children(recursive=True):
            handler.kill()
        current_process.kill()

    def apply_runtime_settings(self, new_settings: dict):
        try:
            self.settings = new_settings
            self.max_downloads = int(new_settings.get("max_downloads", 3) or 3)

            if hasattr(self, "default_downloader") and self.default_downloader:
                dd = self.default_downloader
                dd.max_workers = self.max_downloads
                dd.folder_structure = new_settings.get("folder_structure", "default")

                dd.size_filter_enabled = bool(new_settings.get("size_filter_enabled", False))
                dd.min_size = float(new_settings.get("min_size_mb", 0) or 0) * 1024 * 1024
                dd.max_size = float(new_settings.get("max_size_mb", 0) or 0) * 1024 * 1024

                try:
                    dd.file_naming_mode = int(new_settings.get("file_naming_mode", 0) or 0)
                except Exception:
                    pass

                try:
                    dd.download_retry_attempts = int(new_settings.get("download_retry_attempts", 3) or 3)
                except Exception:
                    pass

            if hasattr(self, "refresh_download_settings"):
                try:
                    self.refresh_download_settings()
                except Exception:
                    pass

            self.add_log_message_safe("Settings applied.")
        except Exception as e:
            self.add_log_message_safe(f"Error applying settings: {e}")

    def open_download_folder(self, event=None):
        if self.download_folder and os.path.exists(self.download_folder):
            if sys.platform == "win32":
                os.startfile(self.download_folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.download_folder])
            else:
                subprocess.Popen(["xdg-open", self.download_folder])
        else:
            messagebox.showerror(self.tr("Error"), self.tr("La carpeta no existe o no es válida."))

    def on_click(self, event):
        widgets_to_ignore = [self.menu_bar]

        for frame in [self.archivo_menu_frame, self.ayuda_menu_frame, self.donaciones_menu_frame]:
            if frame and frame.winfo_exists():
                widgets_to_ignore.append(frame)
                widgets_to_ignore.extend(self.get_all_children(frame))

        if event.widget not in widgets_to_ignore:
            self.close_all_menus()

    def get_all_children(self, widget):
        children = widget.winfo_children()
        all_children = list(children)
        for child in children:
            all_children.extend(self.get_all_children(child))
        return all_children

    def create_custom_menubar(self):
        archivo_button = ctk.CTkButton(
            self.menu_bar,
            text=self.tr("Archivo"),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=self.toggle_archivo_menu
        )
        archivo_button.pack(side="left")
        archivo_button.bind("<Button-1>", lambda e: "break")

        about_button = ctk.CTkButton(
            self.menu_bar,
            text=self.tr("About"),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=self.about_window.show_about
        )
        about_button.pack(side="left")
        about_button.bind("<Button-1>", lambda e: "break")

        donors_button = ctk.CTkButton(
            self.menu_bar,
            text=self.tr("Patreons"),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=self.show_donors_modal
        )
        donors_button.pack(side="left")
        donors_button.bind("<Button-1>", lambda e: "break")

        self.archivo_menu_frame = None
        self.ayuda_menu_frame = None
        self.donaciones_menu_frame = None

        def on_enter(event, frame):
            frame.configure(fg_color="gray25")

        def on_leave(event, frame):
            frame.configure(fg_color="transparent")

        if self.github_icon:
            resized_github_icon = self.github_icon.resize((16, 16), Image.Resampling.LANCZOS)
            resized_github_icon = ctk.CTkImage(resized_github_icon)

            github_frame = ctk.CTkFrame(self.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            github_frame.pack(side="right", padx=5)

            github_label = ctk.CTkLabel(
                github_frame,
                image=resized_github_icon,
                text=f" Star {self.github_stars}",
                compound="left",
                font=("Arial", 12)
            )
            github_label.pack(padx=5, pady=5)

            github_frame.bind("<Enter>", lambda e: on_enter(e, github_frame))
            github_frame.bind("<Leave>", lambda e: on_leave(e, github_frame))
            github_label.bind("<Enter>", lambda e: on_enter(e, github_frame))
            github_label.bind("<Leave>", lambda e: on_leave(e, github_frame))
            github_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/emy69/CoomerDL"))

        self.discord_icon = self.load_discord_icon()
        if self.discord_icon:
            resized_discord_icon = self.discord_icon.resize((16, 16), Image.Resampling.LANCZOS)
            resized_discord_icon = ctk.CTkImage(resized_discord_icon)

            discord_frame = ctk.CTkFrame(self.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            discord_frame.pack(side="right", padx=5)

            discord_label = ctk.CTkLabel(
                discord_frame,
                image=resized_discord_icon,
                text="Discord",
                compound="left"
            )
            discord_label.pack(padx=5, pady=5)

            discord_frame.bind("<Enter>", lambda e: on_enter(e, discord_frame))
            discord_frame.bind("<Leave>", lambda e: on_leave(e, discord_frame))
            discord_label.bind("<Enter>", lambda e: on_enter(e, discord_frame))
            discord_label.bind("<Leave>", lambda e: on_leave(e, discord_frame))
            discord_label.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/ku8gSPsesh"))

        self.new_icon = self.load_patreon_icon()
        if self.new_icon:
            resized_new_icon = self.new_icon.resize((16, 16), Image.Resampling.LANCZOS)
            resized_new_icon = ctk.CTkImage(resized_new_icon)

            new_icon_frame = ctk.CTkFrame(self.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            new_icon_frame.pack(side="right", padx=5)

            new_icon_label = ctk.CTkLabel(
                new_icon_frame,
                image=resized_new_icon,
                text="Patreon",
                compound="left"
            )
            new_icon_label.pack(padx=5, pady=5)

            new_icon_frame.bind("<Enter>", lambda e: on_enter(e, new_icon_frame))
            new_icon_frame.bind("<Leave>", lambda e: on_leave(e, new_icon_frame))
            new_icon_label.bind("<Enter>", lambda e: on_enter(e, new_icon_frame))
            new_icon_label.bind("<Leave>", lambda e: on_leave(e, new_icon_frame))
            new_icon_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.patreon.com/Emy69"))

    def show_donors_modal(self):
        donors_modal = DonorsModal(self, self.tr)
        donors_modal.focus_set()

    def toggle_archivo_menu(self):
        if self.archivo_menu_frame and self.archivo_menu_frame.winfo_exists():
            self.archivo_menu_frame.destroy()
        else:
            self.close_all_menus()
            self.archivo_menu_frame = self.create_menu_frame(
                [
                    (self.tr("Configuraciones"), self.settings_window.open_settings),
                    ("separator", None),
                    (self.tr("Salir"), self.quit),
                ],
                x=0
            )

    def create_menu_frame(self, options, x):
        menu_frame = ctk.CTkFrame(self, corner_radius=5, fg_color="gray25", border_color="black", border_width=1)
        menu_frame.place(x=x, y=30)
        menu_frame.configure(border_width=1, border_color="black")
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
                    command=lambda cmd=option[1]: cmd()
                )
                btn.pack(fill="x", padx=5, pady=2)
                btn.bind("<Button-1>", lambda e: "break")

        return menu_frame

    def close_all_menus(self):
        for menu_frame in [self.archivo_menu_frame, self.ayuda_menu_frame, self.donaciones_menu_frame]:
            if menu_frame and menu_frame.winfo_exists():
                menu_frame.destroy()

    # -------------------------------------------------------------------------
    # Imágenes / iconos
    # -------------------------------------------------------------------------
    def create_photoimage(self, path, size=(32, 32)):
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def load_and_resize_image(self, path, size=(20, 20)):
        img = Image.open(path)
        return ctk.CTkImage(img, size=size)

    def load_icon(self, icon_path, icon_name):
        try:
            img = Image.open(icon_path)
            return img
        except Exception as e:
            self.add_log_message_safe(f"Error al cargar el icono {icon_name}: {e}")
            return None

    def load_github_icon(self):
        return self.load_icon("resources/img/iconos/ui/social/github-logo-24.png", "GitHub")

    def load_discord_icon(self):
        return self.load_icon("resources/img/iconos/ui/social/discord-alt-logo-24.png", "Discord")

    def load_patreon_icon(self):
        return self.load_icon("resources/img/iconos/ui/social/patreon-logo-24.png", "Patreon")

    # -------------------------------------------------------------------------
    # Downloaders
    # -------------------------------------------------------------------------
    def setup_erome_downloader(self, is_profile_download=False):
        self.erome_downloader = self.downloader_factory.create_erome_downloader(
            is_profile_download=is_profile_download
        )

    def setup_simpcity_downloader(self):
        self.simpcity_downloader = self.downloader_factory.create_simpcity_downloader()

    def setup_bunkr_downloader(self):
        self.bunkr_downloader = self.downloader_factory.create_bunkr_downloader()

    def setup_general_downloader(self):
        self.general_downloader = self.downloader_factory.create_general_downloader()

    def setup_jpg5_downloader(self):
        self.active_downloader = self.downloader_factory.create_jpg5_downloader(
            self.url_entry.get().strip()
        )

    # -------------------------------------------------------------------------
    # Carpeta
    # -------------------------------------------------------------------------
    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.save_download_folder(folder_selected)
            self.folder_path.configure(text=folder_selected)

    # -------------------------------------------------------------------------
    # Progreso
    # -------------------------------------------------------------------------
    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None, status=None):
        self.progress_manager.update_progress(downloaded, total, file_id, file_path, speed, eta, status=status)

    def remove_progress_bar(self, file_id):
        self.progress_manager.remove_progress_bar(file_id)

    def update_global_progress(self, completed_files, total_files):
        self.progress_manager.update_global_progress(completed_files, total_files)

    def toggle_progress_details(self):
        self.progress_manager.toggle_progress_details()

    def center_progress_details_frame(self):
        self.progress_manager.center_progress_details_frame()

    # -------------------------------------------------------------------------
    # Descargas
    # -------------------------------------------------------------------------
    def log_error(self, error_message):
        self.errors.append(error_message)
        self.add_log_message_safe(f"Error: {error_message}")

    def wrapped_download(self, download_method, *args):
        try:
            download_method(*args)
        finally:
            self.active_downloader = None
            self.enable_widgets()
            self.export_logs()

    def start_download(self):
        url = self.url_entry.get().strip()

        if not self.download_folder:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, selecciona una carpeta de descarga."))
            return

        if not url:
            messagebox.showerror(self.tr("Error"), self.tr("Por favor, introduce una URL válida."))
            return

        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.download_start_time = datetime.datetime.now()
        self.errors = []
        self.warnings = []
        download_all = True

        parsed_url = urlparse(url)

        if "erome.com" in url:
            self.add_log_message_safe(self.tr("Descargando Erome"))
            is_profile_download = "/a/" not in url
            self.setup_erome_downloader(is_profile_download=is_profile_download)
            self.active_downloader = self.erome_downloader

            if "/a/" in url:
                self.add_log_message_safe(self.tr("URL del álbum"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(
                        self.active_downloader.process_album_page,
                        url,
                        self.download_folder,
                        self.download_images_check.get(),
                        self.download_videos_check.get(),
                    ),
                    daemon=True
                )
            else:
                self.add_log_message_safe(self.tr("URL del perfil"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(
                        self.active_downloader.process_profile_page,
                        url,
                        self.download_folder,
                        self.download_images_check.get(),
                        self.download_videos_check.get(),
                    ),
                    daemon=True
                )

        elif re.search(r"https?://([a-z0-9-]+\.)?bunkr\.[a-z]{2,}", url):
            self.add_log_message_safe(self.tr("Descargando Bunkr"))
            self.setup_bunkr_downloader()
            self.active_downloader = self.bunkr_downloader

            if any(sub in url for sub in ["/v/", "/i/", "/f/"]):
                self.add_log_message_safe(self.tr("URL del post"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.bunkr_downloader.descargar_post_bunkr, url),
                    daemon=True
                )
            else:
                self.add_log_message_safe(self.tr("URL del perfil"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.bunkr_downloader.descargar_perfil_bunkr, url),
                    daemon=True
                )

        elif parsed_url.netloc in ["coomer.st", "kemono.cr"]:
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
                return

            self.add_log_message_safe(
                self.tr("Servicio extraído: {service} del sitio: {site}", service=service, site=site)
            )

            if post is not None:
                self.add_log_message_safe(self.tr("Descargando post único..."))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.start_ck_post_download, site, service, user, post),
                    daemon=True
                )
            else:
                query, offset = extract_ck_query(parsed_url)
                self.add_log_message_safe(self.tr("Descargando todo el contenido del usuario..."))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.start_ck_profile_download, site, service, user, query, download_all, offset),
                    daemon=True
                )

        elif "simpcity.cr" in url:
            self.add_log_message_safe(self.tr("Descargando SimpCity"))
            self.setup_simpcity_downloader()
            self.active_downloader = self.simpcity_downloader
            download_thread = threading.Thread(
                target=self.wrapped_download,
                args=(self.active_downloader.download_images_from_simpcity, url),
                daemon=True
            )

        elif "jpg5.su" in url:
            self.add_log_message_safe(self.tr("Descargando desde Jpg5"))
            self.setup_jpg5_downloader()
            download_thread = threading.Thread(
                target=self.wrapped_download,
                args=(self.active_downloader.descargar_imagenes,),
                daemon=True
            )

        else:
            self.add_log_message_safe(self.tr("URL no válida"))
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            return

        download_thread.start()
        self.app_state.current_download_thread = download_thread

    def start_ck_profile_download(self, site, service, user, query, download_all, initial_offset):
        download_info = self.active_downloader.download_media(
            site,
            user,
            service,
            query=query,
            download_all=download_all,
            initial_offset=initial_offset
        )
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
        return download_info

    def start_ck_post_download(self, site, service, user, post):
        download_info = self.active_downloader.download_single_post(site, post, service, user)
        if download_info:
            self.add_log_message_safe(f"Download info: {download_info}")
        return download_info

    def extract_user_id(self, url):
        self.add_log_message_safe(self.tr("Extrayendo ID del usuario del URL: {url}", url=url))
        match = re.search(r"/user/([^/?]+)", url)
        if match:
            user_id = match.group(1)
            self.add_log_message_safe(self.tr("ID del usuario extraído: {user_id}", user_id=user_id))
            return user_id
        else:
            self.add_log_message_safe(self.tr("No se pudo extraer el ID del usuario."))
            messagebox.showerror(self.tr("Error"), self.tr("No se pudo extraer el ID del usuario."))
            return None

    def extract_post_id(self, url):
        match = re.search(r"/post/([^/?]+)", url)
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
            try:
                self.active_downloader.request_cancel()
            except Exception:
                pass
            self.active_downloader = None
            self.clear_progress_bars()
        else:
            self.add_log_message_safe(self.tr("No hay una descarga en curso para cancelar."))

        self.enable_widgets()

    def clear_progress_bars(self):
        for file_id in list(self.progress_bars.keys()):
            self.remove_progress_bar(file_id)

    # -------------------------------------------------------------------------
    # Logs
    # -------------------------------------------------------------------------
    def add_log_message_safe(self, message: str):
        if not hasattr(self, "all_logs") or self.all_logs is None:
            self.all_logs = []

        if not hasattr(self, "errors") or self.errors is None:
            self.errors = []

        self.all_logs.append(message)

        try:
            if hasattr(self, "log_textbox") and self.log_textbox:
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", message + "\n")

                if MAX_LOG_LINES is not None:
                    self.limit_log_lines()

                self.log_textbox.configure(state="disabled")

                if getattr(self, "autoscroll_logs_var", None) and self.autoscroll_logs_var.get():
                    self.log_textbox.see("end")
            else:
                if not hasattr(self, "_log_buffer") or self._log_buffer is None:
                    self._log_buffer = []
                self._log_buffer.append(message)
        except Exception:
            if not hasattr(self, "_log_buffer") or self._log_buffer is None:
                self._log_buffer = []
            self._log_buffer.append(message)

    def flush_log_buffer(self):
        if not hasattr(self, "_log_buffer") or not self._log_buffer:
            return
        pending = list(self._log_buffer)
        self._log_buffer.clear()
        for msg in pending:
            self.add_log_message_safe(msg)

    def limit_log_lines(self):
        log_lines = self.log_textbox.get("1.0", "end-1c").split("\n")
        if MAX_LOG_LINES is not None and len(log_lines) > MAX_LOG_LINES:
            overflow = len(log_lines) - MAX_LOG_LINES
            self.log_textbox.delete("1.0", f"{overflow}.0")

    def export_logs(self):
        log_folder = "resources/config/logs/"
        Path(log_folder).mkdir(parents=True, exist_ok=True)
        log_file_path = Path(log_folder) / f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            if self.active_downloader:
                total_files = getattr(self.active_downloader, "total_files", 0)
                completed_files = getattr(self.active_downloader, "completed_files", 0)
                skipped_files = getattr(self.active_downloader, "skipped_files", [])
                failed_files = getattr(self.active_downloader, "failed_files", [])
            else:
                total_files = 0
                completed_files = 0
                skipped_files = []
                failed_files = []

            total_images = completed_files if self.download_images_check.get() else 0
            total_videos = completed_files if self.download_videos_check.get() else 0
            errors = len(self.errors)
            warnings = len(self.warnings)
            duration = datetime.datetime.now() - self.download_start_time if self.download_start_time else "N/A"

            skipped_files_summary = "\n".join(skipped_files)
            failed_files_summary = "\n".join(failed_files)

            summary = (
                f"Total de archivos descargados: {total_files}\n"
                f"Total de imágenes descargadas: {total_images}\n"
                f"Total de videos descargados: {total_videos}\n"
                f"Errores: {errors}\n"
                f"Advertencias: {warnings}\n"
                f"Tiempo total de descarga: {duration}\n\n"
                f"Archivos saltados:\n{skipped_files_summary}\n\n"
                f"Archivos fallidos:\n{failed_files_summary}\n\n"
            )

            with open(log_file_path, "w", encoding="utf-8") as file:
                file.write(summary)
                file.write("\n--- LOGS COMPLETOS ---\n")
                file.write("\n".join(self.all_logs))

            self.add_log_message_safe(f"Logs exportados exitosamente a {log_file_path}")
        except Exception as e:
            self.add_log_message_safe(f"No se pudo exportar los logs: {e}")

    # -------------------------------------------------------------------------
    # Clipboard
    # -------------------------------------------------------------------------
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
                    self.url_entry.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                self.url_entry.insert(tk.INSERT, clipboard_text)
            else:
                self.add_log_message_safe(self.tr("No hay texto en el portapapeles para pegar."))
        except tk.TclError as e:
            self.add_log_message_safe(f"{self.tr('Error al pegar desde el portapapeles')}: {e}")

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

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.context_menu.grab_release()

    # -------------------------------------------------------------------------
    # Queue / widgets
    # -------------------------------------------------------------------------
    def check_update_queue(self):
        while not self.update_queue.empty():
            task = self.update_queue.get_nowait()
            task()
        self.after(100, self.check_update_queue)

    def enable_widgets(self):
        self.update_queue.put(lambda: self.download_button.configure(state="normal"))
        self.update_queue.put(lambda: self.cancel_button.configure(state="disabled"))

    def update_max_downloads(self, max_downloads):
        self.max_downloads = max_downloads

        for attr_name in ("general_downloader", "erome_downloader", "bunkr_downloader"):
            downloader = getattr(self, attr_name, None)
            if not downloader:
                continue

            try:
                if hasattr(downloader, "update_max_downloads"):
                    downloader.update_max_downloads(max_downloads)
                elif hasattr(downloader, "set_download_mode"):
                    current_mode = getattr(downloader, "download_mode", "multi")
                    downloader.set_download_mode(current_mode, max_downloads)
                else:
                    downloader.max_workers = max_downloads
            except Exception as e:
                print(f"[update_max_downloads] Error updating {attr_name}: {e}")

    def on_hover_enter(self, event):
        self.folder_path.configure(font=("Arial", 13, "underline"))

    def on_hover_leave(self, event):
        self.folder_path.configure(font=("Arial", 13))

    # -------------------------------------------------------------------------
    # GitHub / updates
    # -------------------------------------------------------------------------
    def get_github_stars(self, user: str, repo: str, timeout: float = 2.5) -> int:
        try:
            url = f"https://api.github.com/repos/{user}/{repo}"
            headers = {
                "User-Agent": "CoomerDL",
                "Accept": "application/vnd.github+json",
            }
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return int(data.get("stargazers_count", 0))
        except Exception:
            self.add_log_message_safe(self.tr("Offline mode: GitHub stars could not be retrieved."))
            return 0

    def parse_version_string(self, version_str):
        try:
            return tuple(int(p) for p in version_str[1:].split("."))
        except (ValueError, IndexError):
            return 0, 0, 0

    def check_for_new_version(self, startup_check=False):
        repo_owner = "emy69"
        repo_name = "CoomerDL"
        github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

        try:
            response = requests.get(github_api_url, timeout=5)
            response.raise_for_status()
            latest_release = response.json()

            latest_tag = latest_release.get("tag_name")
            latest_url = latest_release.get("html_url")

            if latest_tag and latest_url:
                current_version_parsed = self.parse_version_string(VERSION)
                latest_version_parsed = self.parse_version_string(latest_tag)

                if latest_version_parsed > current_version_parsed:
                    self.latest_release_url = latest_url
                    self.after(0, functools.partial(self.show_update_alert, latest_tag))
                    if not startup_check:
                        self.after(
                            0,
                            lambda: messagebox.showinfo(
                                self.tr("Update Available"),
                                self.tr(
                                    "A new version ({latest_tag}) is available! Please download it from GitHub.",
                                    latest_tag=latest_tag
                                )
                            )
                        )
                else:
                    if not startup_check:
                        self.after(
                            0,
                            lambda: messagebox.showinfo(
                                self.tr("No Updates"),
                                self.tr("You are running the latest version.")
                            )
                        )
            else:
                if not startup_check:
                    self.after(
                        0,
                        lambda: messagebox.showwarning(
                            self.tr("Update Check Failed"),
                            self.tr("Could not retrieve latest version information from GitHub.")
                        )
                    )

        except requests.exceptions.RequestException as e:
            if self._is_offline_error(e):
                self.add_log_message_safe(self.tr("Offline mode: could not check for updates."))
                if not startup_check:
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            self.tr("No Internet connection"),
                            self.tr(
                                "We couldn't check for updates. You may not be connected to the Internet right now.\n\nThe app will continue to work in offline mode."
                            )
                        )
                    )
            else:
                self.add_log_message_safe(f"Error checking for updates: {e}")
                if not startup_check:
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            self.tr("Network Error"),
                            self.tr("Could not connect to GitHub to check for updates. Please check your internet connection.")
                        )
                    )
        except Exception as e:
            self.add_log_message_safe(f"An unexpected error occurred during update check: {e}")
            if not startup_check:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        self.tr("Error"),
                        self.tr("An unexpected error occurred during update check.")
                    )
                )

    def show_update_alert(self, latest_tag):
        self.update_alert_label.configure(
            text=self.tr("New version ({latest_tag}) available!", latest_tag=latest_tag)
        )
        self.update_alert_frame.pack(side="top", fill="x")

        self.input_frame.pack_forget()
        self.input_frame.pack(fill="x", padx=20, pady=20)

        self.options_frame.pack_forget()
        self.options_frame.pack(pady=10, fill="x", padx=20)

        self.action_frame.pack_forget()
        self.action_frame.pack(pady=10, fill="x", padx=20)

        self.log_textbox.pack_forget()
        self.log_textbox.pack(pady=(10, 0), padx=20, fill="both", expand=True)

        self.progress_frame.pack_forget()
        self.progress_frame.pack(pady=(0, 10), fill="x", padx=20)

    def open_latest_release(self):
        if self.latest_release_url:
            webbrowser.open(self.latest_release_url)
        else:
            messagebox.showwarning(self.tr("No Release Found"), self.tr("No latest release URL available."))

    def _is_offline_error(self, err: Exception) -> bool:
        s = str(err)
        return (
            isinstance(err, requests.exceptions.ConnectionError)
            or "NameResolutionError" in s
            or "getaddrinfo failed" in s
            or "Failed to establish a new connection" in s
            or "Max retries exceeded" in s
        )
