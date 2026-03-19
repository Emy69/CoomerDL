import datetime
import os
import subprocess
import sys
import threading

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QFileDialog,
)

from app.controllers.main_controller import MainController
from app.models.app_state import AppState
from app.services.settings_service import SettingsService
from app.services.translation_service import TranslationService
from app.services.update_service import UpdateService
from app.services.log_service import LogService
from app.services.url_service import UrlService
from app.adapters.downloader_factory import DownloaderFactory

from app.views.pyside.widgets.download_panel import DownloadPanel
from app.views.pyside.widgets.log_panel import LogPanel
from app.views.pyside.widgets.footer_bar import FooterBar


VERSION = "V0.8.12"
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
        self.update_service = UpdateService(self.tr)
        self.log_service = LogService()
        self.url_service = UrlService()
        self.downloader_factory = DownloaderFactory(self)
        self.main_controller = MainController(self)

        # runtime
        self.active_downloader = None
        self.download_start_time = None
        self.settings = self.settings_service.load_settings()
        self.max_downloads = int(self.settings.get("max_downloads", 3))
        self.latest_release_url = None

        # señales thread-safe
        self.signals = QtSignals()
        self.signals.log_message.connect(self._append_log)
        self.signals.set_download_enabled.connect(self._set_download_enabled)
        self.signals.set_cancel_enabled.connect(self._set_cancel_enabled)
        self.signals.global_progress.connect(self._apply_global_progress)
        self.signals.footer_speed.connect(self.footer_set_speed)
        self.signals.footer_eta.connect(self.footer_set_eta)
        self.signals.clear_logs.connect(self._clear_logs)
        self.signals.show_error_box.connect(self._show_error_dialog)

        self._build_ui()
        self._bind_events()
        self._create_default_downloader()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.download_panel = DownloadPanel(self)
        layout.addWidget(self.download_panel)

        self.log_panel = LogPanel(self)
        layout.addWidget(self.log_panel, 1)

        self.footer_bar = FooterBar(self)
        layout.addWidget(self.footer_bar)

        # adaptadores para reusar MainController actual
        self.url_entry = QtLineEditAdapter(self.download_panel.url_input)
        self.download_images_check = QtCheckBoxAdapter(self.download_panel.images_check)
        self.download_videos_check = QtCheckBoxAdapter(self.download_panel.videos_check)
        self.download_compressed_check = QtCheckBoxAdapter(self.download_panel.compressed_check)

        self.update_folder_label()

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
        # fase 1 PySide: solo progreso global
        self.signals.global_progress.emit(0, 0)
        self.footer_set_speed("Speed: 0 KB/s")
        self.footer_set_eta("ETA: N/A")

    def add_log_message_safe(self, message: str):
        self.log_service.add(message)
        self.signals.log_message.emit(message)

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
        # fase 1: si viene progreso global o individual, usamos el porcentaje recibido
        if total and total > 0:
            self.signals.global_progress.emit(int(downloaded), int(total))

        if speed is not None:
            self.footer_set_speed_from_value(speed)

        if eta is not None:
            self.footer_set_eta_from_value(eta)

        if status is not None:
            self.footer_set_eta(f"ETA: N/A | STATUS:{status}")

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
        self.general_downloader = self.downloader_factory.create_general_downloader()

    def setup_jpg5_downloader(self):
        self.active_downloader = self.downloader_factory.create_jpg5_downloader(
            self.url_entry.get().strip()
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
        self.log_panel.log_text.append(message)
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

        self.log_panel.progress_bar.setValue(percentage)
        self.log_panel.progress_label.setText(f"{percentage}%")

    def _clear_logs(self):
        self.log_panel.log_text.clear()
        self.log_panel.progress_bar.setValue(0)
        self.log_panel.progress_label.setText("0%")
        self.footer_set_speed("Speed: 0 KB/s")
        self.footer_set_eta("ETA: N/A")

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