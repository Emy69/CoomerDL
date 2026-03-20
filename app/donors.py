import os
import json
import requests

from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QWidget,
    QScrollArea,
)


class DonorsWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            response = requests.get(
                "https://emydevs.com/coomer/donadores.php",
                headers={
                    "Accept": "application/json",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/100.0.4896.127 Safari/537.36"
                    ),
                },
                timeout=10,
            )
            response.raise_for_status()
            donors = response.json()
            self.finished.emit(donors if isinstance(donors, list) else [])
        except requests.exceptions.RequestException as exc:
            self.error.emit(f"request:{exc}")
        except json.JSONDecodeError as exc:
            self.error.emit(f"json:{exc}")
        except Exception as exc:
            self.error.emit(f"unknown:{exc}")


class DonorsModal(QDialog):
    def __init__(self, parent, tr):
        super().__init__(parent)
        self.parent = parent
        self.tr = tr

        self.worker_thread = None
        self.worker = None
        self._donor_pixmaps = {}

        self.setWindowTitle(self.tr("Patreons"))
        self.setModal(True)
        self.setFixedSize(600, 600)
        self.setWindowModality(Qt.WindowModal)

        self._build_ui()
        self._center_window()
        self._load_donors_async()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1f1f1f;
                color: white;
            }
            QFrame#mainCard {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 14px;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QLabel[role="title"] {
                font-size: 24px;
                font-weight: 700;
            }
            QLabel[role="status"] {
                font-size: 14px;
                color: gray;
            }
            QLabel[role="note"] {
                font-size: 12px;
                color: gray;
                font-style: italic;
            }
            QLabel[role="name"] {
                font-size: 14px;
                color: #E0E0E0;
            }
            QFrame[role="donorCard"] {
                background-color: transparent;
                border: 1px solid #3b3b3b;
                border-radius: 10px;
            }
            QPushButton {
                min-height: 34px;
                padding: 6px 14px;
                border-radius: 8px;
                border: 1px solid #4a4a4a;
                background-color: #3a3a3a;
                color: white;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(0)

        self.main_card = QFrame()
        self.main_card.setObjectName("mainCard")
        main_layout = QVBoxLayout(self.main_card)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        title_label = QLabel(self.tr("Patreons"))
        title_label.setProperty("role", "title")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(12)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.status_label = QLabel(self.tr("Loading Patreons..."))
        self.status_label.setProperty("role", "status")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.grid_layout.addWidget(self.status_label, 0, 0, 1, 2)

        root_layout.addWidget(self.main_card)

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif layout is not None:
                self._delete_layout(layout)

    def _delete_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._delete_layout(child_layout)

    def _load_icon_pixmap(self, filename):
        icon_dir = os.path.join("resources", "img", "iconos", "donors")
        path = os.path.join(icon_dir, filename)
        if not os.path.exists(path):
            return None

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None

        return pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _ensure_icons_loaded(self):
        if self._donor_pixmaps:
            return

        self._donor_pixmaps = {
            "gold": self._load_icon_pixmap("gold.png"),
            "silver": self._load_icon_pixmap("silver.png"),
            "bronze": self._load_icon_pixmap("bronze.png"),
            "default": self._load_icon_pixmap("default.png"),
        }

    def _load_donors_async(self):
        self.worker_thread = QThread(self)
        self.worker = DonorsWorker()
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._show_donors)
        self.worker.error.connect(self._show_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _show_error(self, raw_error):
        self._clear_grid()

        if raw_error.startswith("request:"):
            msg = raw_error.split(":", 1)[1]
            text = self.tr("Error fetching donors: {error}").format(error=msg)
        elif raw_error.startswith("json:"):
            msg = raw_error.split(":", 1)[1]
            text = self.tr("Error processing donor data: {error}").format(error=msg)
        else:
            msg = raw_error.split(":", 1)[1] if ":" in raw_error else raw_error
            text = self.tr("Error fetching donors: {error}").format(error=msg)

        self.status_label = QLabel(text)
        self.status_label.setProperty("role", "status")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.grid_layout.addWidget(self.status_label, 0, 0, 1, 2)

    def _show_donors(self, donors):
        self._clear_grid()
        self._ensure_icons_loaded()

        columns = 2

        if not donors:
            empty_label = QLabel(self.tr("No donors found."))
            empty_label.setProperty("role", "status")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0, 1, columns)
            return

        def to_float(value):
            try:
                return float(value)
            except Exception:
                return 0.0

        donors.sort(key=lambda x: to_float(x.get("donated_amount", 0)), reverse=True)

        info_label = QLabel(
            self.tr(
                "Note: Donor information is updated every 10th of each month.\n"
                "Names and donation amounts are retrieved from my Patreon page."
            )
        )
        info_label.setProperty("role", "note")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        self.grid_layout.addWidget(info_label, 0, 0, 1, columns)

        for index, donor in enumerate(donors):
            donor_name = donor.get("name", self.tr("Unknown Donor"))

            icon_key = "default"
            icon_pixmap = self._donor_pixmaps.get(icon_key)

            card = QFrame()
            card.setProperty("role", "donorCard")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 10, 10, 10)
            card_layout.setSpacing(10)

            icon_label = QLabel()
            icon_label.setFixedSize(24, 24)
            icon_label.setAlignment(Qt.AlignCenter)
            if icon_pixmap is not None:
                icon_label.setPixmap(icon_pixmap)

            name_label = QLabel(donor_name)
            name_label.setProperty("role", "name")
            name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            name_label.setWordWrap(True)

            card_layout.addWidget(icon_label, 0, Qt.AlignTop)
            card_layout.addWidget(name_label, 1)

            row = (index // columns) + 1
            col = index % columns
            self.grid_layout.addWidget(card, row, col)

    def update_donor_data(self, new_donors):
        self._show_donors(new_donors)

    def _center_window(self):
        if self.parent is not None:
            parent_geometry = self.parent.frameGeometry()
            dialog_geometry = self.frameGeometry()
            dialog_geometry.moveCenter(parent_geometry.center())
            self.move(dialog_geometry.topLeft())
            return

        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            dialog_geometry = self.frameGeometry()
            dialog_geometry.moveCenter(available.center())
            self.move(dialog_geometry.topLeft())

    def show_modal(self):
        self.exec()