import datetime
from email.mime import text
import os
import subprocess
import sys
import threading

from pathlib import Path
import time
from typing import Optional
from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
)

from app.controllers.main_controller import MainController
from app.models.app_state import AppState
from app.services.settings_service import SettingsService
from app.services.translation_service import TranslationService
from app.services.log_service import LogService
from app.services.url_service import UrlService
from app.adapters.downloader_factory import DownloaderFactory

from app.views.pyside.widgets.download_panel import DownloadPanel
from app.views.pyside.widgets.log_panel import LogPanel
from app.views.pyside.widgets.footer_bar import FooterBar
from app.views.pyside.dialogs.settings_dialog import SettingsDialog
from app.views.pyside.progress.progress_controller import ProgressController
from app.adapters.pyside_frontend_bridge import PySideFrontendBridge
from app.about_window import AboutWindow
from app.donors import DonorsModal
from app.views.pyside.dialogs.startup_community_dialog import StartupCommunityDialog

VERSION = "V1.1.0"
MAX_LOG_LINES = None


class QtLineEditAdapter:
    def __init__(self, widget):
        self.widget = widget

    def get(self):
        return self.widget.text()


class QtCheckBoxAdapter:
    def __init__(self, widget):
        self.widget = widget

    def get(self):
        return self.widget.isChecked()


class QtSignals(QObject):
    log_message = Signal(str)
    set_download_enabled = Signal(bool)
    set_cancel_enabled = Signal(bool)
    global_progress = Signal(int, int)
    footer_speed = Signal(str)
    footer_eta = Signal(str)
    footer_total_size = Signal(str)
    clear_logs = Signal()
    show_error_box = Signal(str, str)


class PySideMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.version = VERSION
        self.setWindowTitle(f"Downloader [{VERSION}]")
        self.resize(1000, 700)

        # estado y servicios
        self.app_state = AppState()
        self.settings_service = SettingsService()
        self.app_state.language = self.settings_service.load_language_preference("en")
        self.app_state.download_folder = self.settings_service.load_download_folder("downloads")
        self.download_folder = self.app_state.download_folder

        self.translation_service = TranslationService(language=self.app_state.language)
        self.log_service = LogService()
        self.url_service = UrlService()

        self.frontend_bridge = PySideFrontendBridge(self)
        self.downloader_factory = DownloaderFactory(self.frontend_bridge, app=self)
        self.main_controller = MainController(self)
        self.progress_controller = ProgressController(self)
        # runtime
        self.active_downloader = None
        self.download_start_time = None
        self.settings = self.settings_service.load_settings()
        self.max_downloads = int(self.settings.get("max_downloads", 3))
        self.latest_release_url = None
        
        self._active_progress = {}
        self._active_progress_lock = threading.Lock()

        # señales thread-safe
        self.signals = QtSignals()
        self.signals.log_message.connect(self._append_log)
        self.signals.set_download_enabled.connect(self._set_download_enabled)
        self.signals.set_cancel_enabled.connect(self._set_cancel_enabled)
        self.signals.global_progress.connect(self._apply_global_progress)
        self.signals.footer_speed.connect(self.footer_set_speed)
        self.signals.footer_eta.connect(self.footer_set_eta)
        self.signals.footer_total_size.connect(self.footer_set_total_size)
        self.signals.clear_logs.connect(self._clear_logs)
        self.signals.show_error_box.connect(self._show_error_dialog)

        self._build_ui()
        self._bind_events()
        self._create_default_downloader()
        self.update_ui_texts()
        
        self._smoothed_total_speed = 0.0
        self._last_footer_activity_ts = 0.0
        self._footer_hold_seconds = 1.0

        self.hide()
        QTimer.singleShot(0, self.show_startup_community_dialog)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_row = QHBoxLayout()

        menu_bar = self.menuBar()

        self.file_menu = menu_bar.addMenu("File")

        self.settings_action = self.file_menu.addAction("Settings")
        self.settings_action.triggered.connect(self.open_settings_dialog)

        self.help_action = QAction("About", self)
        self.help_action.triggered.connect(self.open_about_window)
        menu_bar.addAction(self.help_action)

        self.support_action = QAction("Patreons", self)
        self.support_action.triggered.connect(self.open_donors_modal)
        menu_bar.addAction(self.support_action)

        

        top_row = QHBoxLayout()
        top_row.addStretch(1)

        layout.addLayout(top_row)

        self.download_panel = DownloadPanel(self, tr=self.tr)
        layout.addWidget(self.download_panel)

        self.log_panel = LogPanel(self)
        layout.addWidget(self.log_panel, 1)

        self.footer_bar = FooterBar(self)
        self.footer_bar.progress_details_button.clicked.connect(self.toggle_progress_details)
        layout.addWidget(self.footer_bar)

        self.url_entry = QtLineEditAdapter(self.download_panel.url_input)
        self.download_images_check = QtCheckBoxAdapter(self.download_panel.images_check)
        self.download_videos_check = QtCheckBoxAdapter(self.download_panel.videos_check)
        self.download_compressed_check = QtCheckBoxAdapter(self.download_panel.compressed_check)
        
        self.only_this_url_check = QtCheckBoxAdapter(self.download_panel.only_this_url_check)
        self.autoscroll_log_check = QtCheckBoxAdapter(self.download_panel.autoscroll_log_check)

        self.update_folder_label()
        
    def toggle_progress_details(self):
        self.progress_controller.toggle_dialog()

    def remove_progress_bar(self, item_key):
        self.progress_controller.remove_item(str(item_key))

    def center_progress_details_frame(self):
        pass
    
    def open_settings_dialog(self):
        dialog = SettingsDialog(
            parent=self,
            tr=self.tr,
            load_translations=self.load_translations,
            update_ui_texts=self.update_ui_texts,
            save_language_preference=self.save_language_preference,
            version=self.version,
            downloader=getattr(self, "active_downloader", None),
            on_settings_changed=self.apply_runtime_settings,
        )
        dialog.exec()
        
    def open_about_window(self):
        dialog = AboutWindow(self, self.tr, self.version)
        dialog.show_about()
    
    def open_donors_modal(self):
        dialog = DonorsModal(self, self.tr)
        dialog.show_modal()
    
    def show_startup_community_dialog(self):
        should_show = self.settings_service.get("startup_show_community_message", True)

        if not should_show:
            self.show()
            return

        dialog = StartupCommunityDialog(
            parent=self,
            initial_language=self.app_state.language
        )

        if dialog.exec():
            selected_language = dialog.selected_language()
            self.save_language_preference(selected_language)
            self.load_translations(selected_language)
            self.update_ui_texts()

        self.show()
            
    def load_translations(self, language=None):
        target_language = language or self.app_state.language
        self.app_state.language = target_language
        self.translation_service.set_language(target_language)

    def save_language_preference(self, language):
        self.app_state.language = language
        self.settings_service.save_language_preference(language)
        self.translation_service.set_language(language)

    def update_ui_texts(self):
        self.download_panel.url_label.setText(self.tr("URL_LABEL"))
        self.download_panel.browse_button.setText(self.tr("SELECT_FOLDER"))
        self.download_panel.images_check.setText(self.tr("DOWNLOAD_IMAGES"))
        self.download_panel.videos_check.setText(self.tr("DOWNLOAD_VIDEOS"))
        self.download_panel.only_this_url_check.setText(self.tr("ONLY_THIS_URL"))
        self.download_panel.autoscroll_log_check.setText(self.tr("AUTO_SCROLL_LOG"))
        self.download_panel.compressed_check.setText(self.tr("DOWNLOAD_COMPRESSED"))
        self.download_panel.download_button.setText(self.tr("DOWNLOAD"))
        self.download_panel.cancel_button.setText(self.tr("CANCEL_DOWNLOAD"))

        if hasattr(self, "file_menu"):
            self.file_menu.setTitle(self.tr("File"))
        if hasattr(self, "settings_action"):
            self.settings_action.setText(self.tr("Settings"))
        if hasattr(self, "help_action"):
            self.help_action.setText(self.tr("About"))
        if hasattr(self, "support_action"):
            self.support_action.setText(self.tr("Patreons"))

        if hasattr(self, "footer_bar") and hasattr(self.footer_bar, "progress_details_button"):
            self.footer_bar.progress_details_button.setToolTip(self.tr("Progress Details"))

        if hasattr(self, "progress_controller") and self.progress_controller is not None:
            if hasattr(self.progress_controller, "dialog") and self.progress_controller.dialog is not None:
                self.progress_controller.dialog.tr = self.tr
                self.progress_controller.dialog.retranslate_ui()

        if hasattr(self, "download_panel") and self.download_panel is not None:
            self.download_panel.retranslate_ui()

        self.setWindowTitle(f"Downloader [{self.version}]")
        self.update_folder_label()

    def apply_runtime_settings(self, new_settings: dict):
        try:
            self.settings = new_settings
            self.max_downloads = int(new_settings.get("max_downloads", 3) or 3)

            if hasattr(self, "default_downloader") and self.default_downloader:
                dd = self.default_downloader
                dd.max_workers = self.max_downloads
                dd.folder_structure = new_settings.get("folder_structure", "default")

                try:
                    dd.file_naming_mode = int(new_settings.get("file_naming_mode", 0) or 0)
                except Exception:
                    pass

                try:
                    dd.max_retries = int(new_settings.get("max_retries", 3) or 3)
                except Exception:
                    pass

                try:
                    dd.retry_interval = float(new_settings.get("retry_interval", 2.0) or 2.0)
                except Exception:
                    pass

            self.add_log_message_safe("Settings applied.")
        except Exception as e:
            self.add_log_message_safe(f"Error applying settings: {e}")

    def _bind_events(self):
        self.download_panel.browse_button.clicked.connect(self.select_folder)
        self.download_panel.download_button.clicked.connect(self.start_download)
        self.download_panel.cancel_button.clicked.connect(self.cancel_download)
        self.download_panel.folder_label.linkActivated.connect(lambda _: self.open_download_folder())
        self.download_panel.folder_label.mousePressEvent = lambda event: self.open_download_folder()

    # ------------------------------------------------------------------
    # compatibilidad con backend actual
    # ------------------------------------------------------------------
    def tr(self, key, **kwargs):
        return self.translation_service.tr(key, **kwargs)

    def show_error(self, title, message):
        self.signals.show_error_box.emit(str(title), str(message))

    def prepare_download_ui(self):
        self.download_start_time = datetime.datetime.now()
        self.log_service.clear_runtime()
        self.signals.set_download_enabled.emit(False)
        self.signals.set_cancel_enabled.emit(True)
        self.signals.clear_logs.emit()

    def enable_widgets(self):
        self.signals.set_download_enabled.emit(True)
        self.signals.set_cancel_enabled.emit(False)

    def clear_progress_bars(self):
        if not hasattr(self, "_active_progress"):
            self._active_progress = {}

        if not hasattr(self, "_active_progress_lock"):
            self._active_progress_lock = threading.Lock()

        with self._active_progress_lock:
            self._active_progress.clear()

        self.signals.global_progress.emit(0, 0)
        self.footer_set_speed("Speed: 0 KB/s")
        self.footer_set_eta("ETA: N/A")
        self.footer_set_total_size("Total: 0 B")
        self.progress_controller.clear_all()

    def add_log_message_safe(self, domain_or_message: str, message: Optional[str] = None):
        if message is None:
            domain = "SYSTEM"
            final_message = domain_or_message
        else:
            domain = domain_or_message
            final_message = message

        html = self.log_service.add_domain_log(domain, final_message)
        self.signals.log_message.emit(html)

    def export_logs(self):
        try:
            log_file_path = self.log_service.export_logs(
                active_downloader=self.active_downloader,
                download_images_enabled=bool(self.download_images_check.get()),
                download_videos_enabled=bool(self.download_videos_check.get()),
                download_start_time=self.download_start_time,
            )
            self.signals.log_message.emit(f"Logs exportados exitosamente a {log_file_path}")
        except Exception as e:
            self.signals.log_message.emit(f"No se pudo exportar los logs: {e}")

    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None, status=None):
        if not hasattr(self, "_active_progress"):
            self._active_progress = {}

        if not hasattr(self, "_active_progress_lock"):
            self._active_progress_lock = threading.Lock()

        if not hasattr(self, "_smoothed_total_speed"):
            self._smoothed_total_speed = 0.0

        if not hasattr(self, "_last_footer_activity_ts"):
            self._last_footer_activity_ts = 0.0

        if not hasattr(self, "_footer_hold_seconds"):
            self._footer_hold_seconds = 0.8

        if file_id is None:
            if total and total > 0:
                self.signals.global_progress.emit(int(downloaded), int(total))
            return

        eta_text = "ETA: N/A"
        if eta is not None and eta > 0:
            minutes = int(eta // 60)
            seconds = int(eta % 60)
            eta_text = f"ETA: {minutes}m {seconds}s"

        self.progress_controller.update_item(
            file_id=str(file_id),
            file_path=str(file_path or file_id),
            downloaded=int(downloaded),
            total=int(total),
            eta_text=eta_text,
        )

        progress_key = f"{file_id}|{file_path}" if file_path else str(file_id)
        now = time.monotonic()

        with self._active_progress_lock:
            if total and total > 0 and int(downloaded) < int(total):
                self._active_progress[progress_key] = {
                    "downloaded": int(downloaded),
                    "total": int(total),
                    "speed": float(speed or 0.0),
                    "eta": float(eta or 0.0),
                }
            else:
                self._active_progress.pop(progress_key, None)

            has_active_items = len(self._active_progress) > 0
            if has_active_items:
                self._last_footer_activity_ts = now

            total_speed = sum(
                item["speed"] for item in self._active_progress.values()
                if item["speed"] > 0
            )

            total_downloaded_bytes = sum(
                max(0, item["downloaded"])
                for item in self._active_progress.values()
            )

            total_bytes = sum(
                max(0, item["total"])
                for item in self._active_progress.values()
            )

            total_remaining_bytes = sum(
                max(0, item["total"] - item["downloaded"])
                for item in self._active_progress.values()
            )

        # Suavizado de velocidad para evitar saltos bruscos en archivos pequeños
        if total_speed > 0:
            if self._smoothed_total_speed <= 0:
                self._smoothed_total_speed = total_speed
            else:
                self._smoothed_total_speed = (self._smoothed_total_speed * 0.85) + (total_speed * 0.15)
        else:
            if now - self._last_footer_activity_ts > self._footer_hold_seconds:
                self._smoothed_total_speed = 0.0

        display_speed = self._smoothed_total_speed

        if display_speed > 0:
            if display_speed < 1_048_576:
                self.signals.footer_speed.emit(f"Speed: {display_speed / 1024:.2f} KB/s")
            else:
                self.signals.footer_speed.emit(f"Speed: {display_speed / 1_048_576:.2f} MB/s")
        else:
            self.signals.footer_speed.emit("Speed: 0 KB/s")

        if total_remaining_bytes > 0 and display_speed > 0:
            global_eta = total_remaining_bytes / display_speed
            minutes = int(global_eta // 60)
            seconds = int(global_eta % 60)
            self.signals.footer_eta.emit(f"ETA: {minutes}m {seconds}s")
        elif now - self._last_footer_activity_ts > self._footer_hold_seconds:
            self.signals.footer_eta.emit("ETA: N/A")

        if total_bytes > 0:
            self.signals.footer_total_size.emit(
                f"Total: {self._format_bytes(total_downloaded_bytes)} / {self._format_bytes(total_bytes)}"
            )
        elif now - self._last_footer_activity_ts > self._footer_hold_seconds:
            self.signals.footer_total_size.emit("Total: 0 B")

        if status is not None:
            self.signals.footer_eta.emit(f"ETA: N/A | STATUS:{status}")

    def update_global_progress(self, completed_files, total_files):
        self.signals.global_progress.emit(int(completed_files), int(total_files))

    # ------------------------------------------------------------------
    # downloader factory hooks
    # ------------------------------------------------------------------
    def setup_erome_downloader(self, is_profile_download=False):
        self.erome_downloader = self.downloader_factory.create_erome_downloader(
            is_profile_download=is_profile_download
        )

    def setup_simpcity_downloader(self):
        self.simpcity_downloader = self.downloader_factory.create_simpcity_downloader()

    def setup_bunkr_downloader(self):
        self.bunkr_downloader = self.downloader_factory.create_bunkr_downloader()

    def setup_general_downloader(self):
        self.general_downloader = self.downloader_factory.create_general_downloader(self.settings)

    def setup_jpg5_downloader(self):
        self.active_downloader = self.downloader_factory.create_jpg5_downloader(
            self.url_entry.get().strip(),
            progress_manager=None
        )

    def setup_coomerfans_downloader(self, is_profile_download=False):
        self.coomerfans_downloader = self.downloader_factory.create_coomerfans_downloader(
            is_profile_download=is_profile_download
        )

    def _create_default_downloader(self):
        # opcional para compatibilidad con algunos settings runtime
        pass

    # ------------------------------------------------------------------
    # acciones
    # ------------------------------------------------------------------
    def start_download(self):
        self.main_controller.start_download()

    def cancel_download(self):
        self.main_controller.cancel_download()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Seleccionar Carpeta"), self.download_folder or "")
        if folder:
            self.download_folder = folder
            self.app_state.download_folder = folder
            self.settings_service.save_download_folder(folder)
            self.update_folder_label()

    def update_folder_label(self):
        path = self.download_folder or ""
        # texto clickeable visualmente simple
        self.download_panel.folder_label.setText(path)

    def open_download_folder(self):
        if self.download_folder and os.path.exists(self.download_folder):
            if sys.platform == "win32":
                os.startfile(self.download_folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.download_folder])
            else:
                subprocess.Popen(["xdg-open", self.download_folder])
        else:
            self.show_error(self.tr("Error"), self.tr("La carpeta no existe o no es válida."))

    # ------------------------------------------------------------------
    # slots UI
    # ------------------------------------------------------------------
    def _append_log(self, message: str):
        self.log_panel.log_text.insertHtml(message)
        self.log_panel.log_text.insertHtml("<br>")

        if bool(self.autoscroll_log_check.get()):
            scrollbar = self.log_panel.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        if MAX_LOG_LINES is not None:
            doc = self.log_panel.log_text.document()
            while doc.blockCount() > MAX_LOG_LINES:
                cursor = self.log_panel.log_text.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.select(cursor.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()

    def _set_download_enabled(self, enabled: bool):
        self.download_panel.download_button.setEnabled(enabled)

    def _set_cancel_enabled(self, enabled: bool):
        self.download_panel.cancel_button.setEnabled(enabled)

    def _apply_global_progress(self, current: int, total: int):
        if total > 0:
            percentage = int((current / total) * 100)
        else:
            percentage = 0

        self.footer_bar.progress_bar.setValue(percentage)
        self.footer_bar.progress_label.setText(f"{percentage}%")

    def _clear_logs(self):
        self.log_panel.log_text.clear()
        self.footer_bar.progress_bar.setValue(0)
        self.footer_bar.progress_label.setText("0%")
        self.footer_set_speed("Speed: 0 KB/s")
        self.footer_set_eta("ETA: N/A")
        self.footer_set_total_size("Total: 0 B")

    def _show_error_dialog(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    # ------------------------------------------------------------------
    # footer helpers
    # ------------------------------------------------------------------
    def footer_set_speed(self, text: str):
        self.footer_bar.speed_label.setText(text)

    def footer_set_eta(self, text: str):
        self.footer_bar.eta_label.setText(text)

    def footer_set_speed_from_value(self, speed):
        if speed is None:
            self.footer_set_speed("Speed: 0 KB/s")
            return

        if speed < 1_048_576:
            self.footer_set_speed(f"Speed: {speed / 1024:.2f} KB/s")
        else:
            self.footer_set_speed(f"Speed: {speed / 1_048_576:.2f} MB/s")

    def footer_set_eta_from_value(self, eta):
        if eta is None:
            self.footer_set_eta("ETA: N/A")
            return

        minutes = int(eta // 60)
        seconds = int(eta % 60)
        self.footer_set_eta(f"ETA: {minutes}m {seconds}s")
        
    def _format_bytes(self, num_bytes):
        try:
            value = float(num_bytes or 0)
        except Exception:
            value = 0.0

        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0

        while value >= 1024 and idx < len(units) - 1:
            value /= 1024.0
            idx += 1

        if idx == 0:
            return f"{int(value)} {units[idx]}"
        return f"{value:.2f} {units[idx]}"
    
    def footer_set_total_size(self, text: str):
        self.footer_bar.total_size_label.setText(text)