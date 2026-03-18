import customtkinter as ctk

from app.views.tkinter.progress.progress_row import ProgressRow
from app.views.tkinter.progress.progress_window import ProgressWindow
from app.views.tkinter.progress.progress_utils import format_eta, format_speed
from app.views.tkinter.progress.footer_status import FooterStatusController
from app.services.progress_store import ProgressStore, ProgressEntry
from app.services.progress_logic import ProgressLogic
from app.models.progress_item import ProgressItem

class ProgressManager:
    def __init__(self, root, icons, footer_speed_label, footer_eta_label, progress_bar, progress_percentage):
        self.root = root
        self.icons = icons
        self.footer_speed_label = footer_speed_label
        self.footer_eta_label = footer_eta_label
        self.footer_status = FooterStatusController(
            speed_label=self.footer_speed_label,
            eta_label=self.footer_eta_label
        )
        self.progress_bar = progress_bar
        self.progress_percentage = progress_percentage

        self.progress_store = ProgressStore()
        self.progress_logic = ProgressLogic()
        self.progress_window = ProgressWindow(root)

    def create_progress_window(self):
        self.progress_window.ensure_created()

    def close_progress_window(self):
        self.progress_window.close()

    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None, status=None):
        if status is not None:
            self.footer_status.set_status(str(status))
            return

        if file_id is None:
            self._update_global_bar(downloaded, total)
        else:
            self._update_file_progress(downloaded, total, file_id, file_path, eta)

        if speed is not None:
            self.footer_status.set_speed(format_speed(speed))

        if eta is not None:
            self.footer_status.set_eta(format_eta(eta))

    def _update_global_bar(self, downloaded, total):
        if total > 0 and self.progress_bar.winfo_exists():
            percentage = (downloaded / total) * 100
            self.progress_bar.set(downloaded / total)
            self.progress_percentage.configure(text=f"{percentage:.2f}%")
        elif self.progress_bar.winfo_exists():
            self.progress_bar.set(0)
            self.progress_percentage.configure(text="0%")

    def _update_file_progress(self, downloaded, total, file_id, file_path, eta):
        self.create_progress_window()

        progress_item = ProgressItem(
            file_id=file_id,
            file_path=file_path,
            downloaded=downloaded,
            total=total,
            eta=eta
        )

        if not self.progress_logic.should_update_row(progress_item.total):
            row = self.progress_store.get_row(file_id)
            if row:
                self.progress_store.set_item(file_id, progress_item)
                row.update(progress_item)
            return

        if not self.progress_store.has(file_id):
            self.progress_window.hide_empty_message()
            row = ProgressRow(self.progress_window.details_frame, self.icons, progress_item)
            entry = ProgressEntry(item=progress_item, row=row)
            self.progress_store.set(file_id, entry)
        else:
            self.progress_store.set_item(file_id, progress_item)

        row = self.progress_store.get_row(file_id)
        if row:
            row.update(progress_item)

        if self.progress_logic.is_completed(progress_item.downloaded, progress_item.total):
            self.remove_progress_bar(file_id)

    def remove_progress_bar(self, file_id):
        row = self.progress_store.get_row(file_id)
        if not row:
            return

        row.destroy_later(callback=lambda: self._finalize_remove(file_id))

    def _finalize_remove(self, file_id):
        self.progress_store.remove(file_id)

        if self.progress_logic.should_reset_footer(self.progress_store.is_empty()):
            self.progress_window.show_empty_message()
            self.footer_status.reset()

    def update_global_progress(self, completed_files, total_files):
        if total_files > 0 and self.progress_bar.winfo_exists():
            percentage = (completed_files / total_files) * 100
            self.progress_bar.set(completed_files / total_files)
            self.progress_percentage.configure(text=f"{percentage:.2f}%")

    def toggle_progress_details(self):
        self.create_progress_window()
        if self.progress_window.is_visible():
            self.close_progress_window()
        else:
            self.progress_window.show()

    def center_progress_details_frame(self):
        self.progress_window.center()