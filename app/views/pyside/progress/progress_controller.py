from PySide6.QtCore import QObject, Signal, QTimer

from app.views.pyside.progress.progress_item_widget import ProgressItemWidget
from app.views.pyside.progress.progress_dialog import ProgressDialog


class ProgressSignals(QObject):
    upsert_item = Signal(str, int, int, str)
    remove_item = Signal(str)
    clear_all = Signal()
    toggle_dialog = Signal()


class ProgressController:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.dialog = ProgressDialog(parent_window)
        self.signals = ProgressSignals()

        self.items = {}

        self.signals.upsert_item.connect(self._upsert_item)
        self.signals.remove_item.connect(self._remove_item)
        self.signals.clear_all.connect(self._clear_all)
        self.signals.toggle_dialog.connect(self._toggle_dialog)

    def toggle_dialog(self):
        self.signals.toggle_dialog.emit()

    def update_item(self, file_id: str, file_path: str, downloaded: int, total: int, eta_text: str):
        self.signals.upsert_item.emit(f"{file_id}|{file_path}", downloaded, total, eta_text)

    def remove_item(self, file_id: str):
        self.signals.remove_item.emit(file_id)

    def clear_all(self):
        self.signals.clear_all.emit()

    def _upsert_item(self, packed_key: str, downloaded: int, total: int, eta_text: str):
        file_id, file_path = packed_key.split("|", 1)

        if file_id not in self.items:
            widget = ProgressItemWidget(file_path)
            self.items[file_id] = widget
            self.dialog.container_layout.insertWidget(self.dialog.container_layout.count() - 1, widget)
            self.dialog.show_empty(False)

        widget = self.items[file_id]
        widget.update_progress(downloaded, total, eta_text)

        if total > 0 and downloaded >= total:
            QTimer.singleShot(1500, lambda fid=file_id: self._remove_item(fid))

    def _remove_item(self, file_id: str):
        widget = self.items.pop(file_id, None)
        if widget:
            widget.setParent(None)
            widget.deleteLater()

        self.dialog.show_empty(len(self.items) == 0)

    def _clear_all(self):
        for file_id in list(self.items.keys()):
            self._remove_item(file_id)

    def _toggle_dialog(self):
        if self.dialog.isVisible():
            self.dialog.hide()
        else:
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()