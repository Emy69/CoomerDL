from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
)


class DownloadPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.url_label = QLabel("URL de la página web:")
        root.addWidget(self.url_label)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        url_row.addWidget(self.url_input, 1)

        self.browse_button = QPushButton("Seleccionar Carpeta")
        url_row.addWidget(self.browse_button)
        root.addLayout(url_row)

        self.folder_label = QLabel("")
        self.folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.folder_label)

        options_row = QHBoxLayout()
        self.images_check = QCheckBox("Descargar Imágenes")
        self.images_check.setChecked(True)
        options_row.addWidget(self.images_check)

        self.videos_check = QCheckBox("Descargar Vídeos")
        self.videos_check.setChecked(True)
        options_row.addWidget(self.videos_check)

        self.compressed_check = QCheckBox("Descargar Comprimidos")
        self.compressed_check.setChecked(True)
        options_row.addWidget(self.compressed_check)

        options_row.addStretch(1)
        root.addLayout(options_row)

        extra_options_row = QHBoxLayout()

        self.only_this_url_check = QCheckBox("Solo esta URL")
        self.only_this_url_check.setChecked(False)
        self.only_this_url_check.setToolTip(
            "No paginar perfiles o hilos; descargar solo la URL actual."
        )
        extra_options_row.addWidget(self.only_this_url_check)

        self.autoscroll_log_check = QCheckBox("Auto-scroll log")
        self.autoscroll_log_check.setChecked(True)
        extra_options_row.addWidget(self.autoscroll_log_check)

        extra_options_row.addStretch(1)
        root.addLayout(extra_options_row)

        buttons_row = QHBoxLayout()
        self.download_button = QPushButton("Descargar")
        buttons_row.addWidget(self.download_button)

        self.cancel_button = QPushButton("Cancelar Descarga")
        self.cancel_button.setEnabled(False)
        buttons_row.addWidget(self.cancel_button)

        buttons_row.addStretch(1)
        root.addLayout(buttons_row)