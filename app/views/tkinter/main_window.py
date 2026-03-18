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
from app.controllers.main_controller import MainController
from app.services.update_service import UpdateService
from app.services.log_service import LogService
from app.services.url_service import UrlService
from app.views.tkinter.components.menu_bar import MenuBarBuilder
from app.views.tkinter.components.download_panel import DownloadPanelBuilder
from app.views.tkinter.components.log_panel import LogPanelBuilder
from app.views.tkinter.components.footer import FooterBuilder
from app.views.tkinter.components.update_banner import UpdateBannerBuilder
from app.views.tkinter.components.menu_helpers import MenuHelpers
from app.views.tkinter.components.context_menu import ContextMenuHelper
from app.views.tkinter.components.progress_section import ProgressSectionHelper
from app.views.tkinter.components.ui_helpers import UIHelpers




VERSION = "V0.8.12"
MAX_LOG_LINES = None

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
        self.update_service = UpdateService(self.tr)
        self.log_service = LogService()
        self.url_service = UrlService()
        self.downloader_factory = DownloaderFactory(self)
        self.main_controller = MainController(self)
        self.menu_helpers = MenuHelpers(self)
        self.context_menu_helper = ContextMenuHelper(self)
        self.progress_section = ProgressSectionHelper(self)
        self.ui_helpers = UIHelpers(self)
        # Compatibilidad temporal con código existente
        self.download_folder = self.app_state.download_folder

        # Estado runtime
        self.errors = self.log_service.errors
        self.warnings = self.log_service.warnings
        self.all_logs = self.log_service.all_logs
        self._log_buffer = self.log_service.buffer
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
        self.github_stars = self.update_service.get_github_stars("emy69", "CoomerDL")
        if self.github_stars == 0:
            self.add_log_message_safe(self.tr("Offline mode: GitHub stars could not be retrieved."))
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
        MenuBarBuilder(self).build()
        UpdateBannerBuilder(self).build()
        DownloadPanelBuilder(self).build()
        LogPanelBuilder(self).build()
        FooterBuilder(self).build()

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
    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def prepare_download_ui(self):
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.download_start_time = datetime.datetime.now()
        self.log_service.clear_runtime()
    
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
        self.ui_helpers.open_download_folder(event)

    def on_click(self, event):
        self.menu_helpers.on_click(event)

    def show_donors_modal(self):
        donors_modal = DonorsModal(self, self.tr)
        donors_modal.focus_set()

    def toggle_archivo_menu(self):
        self.menu_helpers.toggle_archivo_menu()

    def create_menu_frame(self, options, x):
        return self.menu_helpers.create_menu_frame(options, x)

    def close_all_menus(self):
        self.menu_helpers.close_all_menus()
        
    def get_all_children(self, widget):
        return self.menu_helpers.get_all_children(widget)


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
        self.progress_section.update_progress(
            downloaded, total, file_id, file_path, speed, eta, status=status
        )

    def remove_progress_bar(self, file_id):
        self.progress_section.remove_progress_bar(file_id)

    def update_global_progress(self, completed_files, total_files):
        self.progress_section.update_global_progress(completed_files, total_files)

    def toggle_progress_details(self):
        self.progress_section.toggle_progress_details()

    def center_progress_details_frame(self):
        self.progress_section.center_progress_details_frame()

    # -------------------------------------------------------------------------
    # Descargas
    # -------------------------------------------------------------------------
    def log_error(self, error_message):
        self.log_service.errors.append(error_message)
        self.add_log_message_safe(f"Error: {error_message}")

    def start_download(self):
        self.main_controller.start_download()

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
        self.main_controller.cancel_download()

    def clear_progress_bars(self):
        self.progress_section.clear_progress_bars()

    # -------------------------------------------------------------------------
    # Logs
    # -------------------------------------------------------------------------
    def add_log_message_safe(self, message: str):
        self.log_service.add(message)

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
                self.log_service.buffer_message(message)
        except Exception:
            self.log_service.buffer_message(message)

    def flush_log_buffer(self):
        if not self.log_service.has_buffer():
            return

        pending = self.log_service.pop_buffer()
        for msg in pending:
            try:
                if hasattr(self, "log_textbox") and self.log_textbox:
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert("end", msg + "\n")

                    if MAX_LOG_LINES is not None:
                        self.limit_log_lines()

                    self.log_textbox.configure(state="disabled")

                    if getattr(self, "autoscroll_logs_var", None) and self.autoscroll_logs_var.get():
                        self.log_textbox.see("end")
            except Exception:
                pass

    def limit_log_lines(self):
        log_lines = self.log_textbox.get("1.0", "end-1c").split("\n")
        if MAX_LOG_LINES is not None and len(log_lines) > MAX_LOG_LINES:
            overflow = len(log_lines) - MAX_LOG_LINES
            self.log_textbox.delete("1.0", f"{overflow}.0")

    def export_logs(self):
        try:
            log_file_path = self.log_service.export_logs(
                active_downloader=self.active_downloader,
                download_images_enabled=bool(self.download_images_check.get()),
                download_videos_enabled=bool(self.download_videos_check.get()),
                download_start_time=self.download_start_time,
            )
            self.add_log_message_safe(f"Logs exportados exitosamente a {log_file_path}")
        except Exception as e:
            self.add_log_message_safe(f"No se pudo exportar los logs: {e}")

    # -------------------------------------------------------------------------
    # Clipboard
    # -------------------------------------------------------------------------
    def copy_to_clipboard(self):
        self.context_menu_helper.copy_to_clipboard()

    def paste_from_clipboard(self):
        self.context_menu_helper.paste_from_clipboard()

    def cut_to_clipboard(self):
        self.context_menu_helper.cut_to_clipboard()

    def show_context_menu(self, event):
        self.context_menu_helper.show_context_menu(event)

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

    def on_hover_enter(self, event=None):
        self.ui_helpers.on_hover_enter(event)

    def on_hover_leave(self, event=None):
        self.ui_helpers.on_hover_leave(event)

    # -------------------------------------------------------------------------
    # GitHub / updates
    # -------------------------------------------------------------------------

    def check_for_new_version(self, startup_check=False):
        try:
            result = self.update_service.check_for_new_version(VERSION)

            latest_tag = result.get("latest_tag")
            latest_url = result.get("latest_url")
            update_available = result.get("update_available", False)

            if latest_url:
                self.latest_release_url = latest_url

            if update_available and latest_tag:
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

        except requests.exceptions.RequestException as e:
            if self.update_service.is_offline_error(e):
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
