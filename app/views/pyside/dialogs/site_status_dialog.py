from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
)

from app.services.settings_service import SettingsService


class SiteStatusDialog(QDialog):
    def __init__(self, parent, translate, offline_sites):
        super().__init__(parent)

        self.settings_service = SettingsService()
        self.translate = translate
        self.offline_sites = offline_sites

        self.setModal(True)
        self.setWindowTitle(self.translate("SITE_STATUS_DIALOG_TITLE"))
        self.resize(560, 300)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title_label = QLabel(self.translate("SITE_STATUS_TITLE"))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title_label)

        lines = [
            self.translate(
                "SITE_STATUS_DOWN_LINE",
                site=site["name"],
                alternative=site["alternative"],
            )
            for site in self.offline_sites
        ]
        lines.append("")
        lines.append(self.translate("SITE_STATUS_JPG5_NOTE"))

        message_label = QLabel("\n".join(lines))
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        message_label.setStyleSheet("""
            font-size: 14px;
            padding: 12px 4px 4px 4px;
        """)
        layout.addWidget(message_label, 1)

        self.dont_show_again_checkbox = QCheckBox(
            self.translate("SITE_STATUS_DONT_SHOW_AGAIN")
        )
        layout.addWidget(self.dont_show_again_checkbox)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)

        ok_button = QPushButton(self.translate("SITE_STATUS_OK_BUTTON"))
        ok_button.clicked.connect(self._save_and_accept)
        buttons_row.addWidget(ok_button)

        layout.addLayout(buttons_row)

    def _save_and_accept(self):
        if self.dont_show_again_checkbox.isChecked():
            self.settings_service.set("show_site_status_warning", False)
        self.accept()
