import requests

from PySide6.QtCore import Qt, QObject, QThread, Signal, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QWidget,
)


class GitHubDataWorker(QObject):
    finished = Signal(str, int, int)

    def __init__(self):
        super().__init__()

    def run(self):
        url = "https://api.github.com/repos/Emy69/CoomerDL"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            repo_data = response.json()

            created_at = repo_data.get("created_at", "N/A")
            created_date = created_at.split("T")[0] if created_at != "N/A" else "N/A"
            stars = int(repo_data.get("stargazers_count", 0))

            releases_url = repo_data.get("releases_url", "").replace("{/id}", "")
            total_downloads = 0

            if releases_url:
                releases_response = requests.get(releases_url, timeout=15)
                releases_response.raise_for_status()
                releases_data = releases_response.json()

                if releases_data:
                    total_downloads = sum(
                        asset.get("download_count", 0)
                        for release in releases_data
                        for asset in release.get("assets", [])
                    )

            self.finished.emit(created_date, total_downloads, stars)
        except Exception as e:
            print(f"Error fetching GitHub data: {e}")
            self.finished.emit("N/A", 0, 0)


class AboutWindow(QDialog):
    def __init__(self, parent, translate, version):
        super().__init__(parent)
        self.parent = parent
        self.translate = translate
        self.version = version

        self.worker_thread = None
        self.worker = None

        self.setWindowTitle(self.translate("ABOUT_WINDOW_TITLE"))
        self.setModal(True)
        self.setFixedSize(360, 540)

        if self.parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.downloads_label = None
        self.date_label = None
        self.stars_button = None

        self.discord_button = None
        self.patron_button = None
        self.x_button = None
        self.footer_label = None
        self.community_label = None
        self.title_label = None

        self._build_ui()
        self._center_window()
        self._load_github_data_async()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1f1f1f;
                color: white;
            }
            QFrame#card {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 14px;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QLabel[role="title"] {
                font-size: 22px;
                font-weight: 700;
            }
            QLabel[role="section"] {
                font-size: 16px;
                font-weight: 700;
            }
            QLabel[role="body"] {
                font-size: 14px;
            }
            QLabel[role="footer"] {
                font-size: 12px;
                font-style: italic;
                color: #cfcfcf;
            }
            QFrame[role="separator"] {
                background-color: #555555;
                max-height: 1px;
                min-height: 1px;
            }
            QPushButton {
                min-height: 36px;
                padding: 6px 12px;
                border-radius: 8px;
                border: 1px solid #4a4a4a;
                background-color: #3a3a3a;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton[role="link"] {
                background-color: transparent;
                color: white;
                border: none;
                text-align: left;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 400;
            }
            QPushButton[role="link"]:hover {
                background-color: #3a3a3a;
                border-radius: 6px;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        self.title_label = QLabel(self.translate("ABOUT_THIS_APP"))
        self.title_label.setProperty("role", "title")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        card_layout.addWidget(self.title_label)

        details = [
            (
                "resources/img/iconos/about/user-account-solid-24.png",
                f"{self.translate('DEVELOPER_LABEL')}: Emy69",
                "developer",
            ),
            (
                "resources/img/iconos/about/git-branch-line.png",
                f"{self.translate('VERSION_LABEL')}: {self.version}",
                "version",
            ),
            (
                "resources/img/iconos/about/download_icon.png",
                f"{self.translate('TOTAL_DOWNLOADS_LABEL')}: {self.translate('LOADING')}",
                "downloads",
            ),
            (
                "resources/img/iconos/about/calendar-event-line.png",
                f"{self.translate('RELEASE_DATE_LABEL')}: {self.translate('LOADING')}",
                "date",
            ),
        ]

        for icon_path, text, key in details:
            row, text_label = self._make_detail_row(icon_path, text)
            card_layout.addWidget(row)

            if key == "downloads":
                self.downloads_label = text_label
            elif key == "date":
                self.date_label = text_label

        separator = QFrame()
        separator.setProperty("role", "separator")
        card_layout.addWidget(separator)

        links_separator = QFrame()
        links_separator.setProperty("role", "separator")
        card_layout.addWidget(links_separator)

        self.community_label = QLabel(self.translate("COMMUNITY_SECTION"))
        self.community_label.setProperty("role", "section")
        self.community_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        card_layout.addWidget(self.community_label)

        self.discord_button = QPushButton(self.translate("JOIN_DISCORD"))
        self.discord_button.setCursor(Qt.PointingHandCursor)
        self.discord_button.clicked.connect(
            lambda: self._open_url("https://discord.gg/6zbjrJbJ3Q")
        )
        card_layout.addWidget(self.discord_button)

        self.stars_button = QPushButton(
            f"{self.translate('GITHUB_STARS_LABEL')}: {self.translate('LOADING')}"
        )
        self.stars_button.setCursor(Qt.PointingHandCursor)
        self.stars_button.clicked.connect(
            lambda: self._open_url("https://github.com/Emy69/CoomerDL")
        )
        card_layout.addWidget(self.stars_button)

        self.patron_button = QPushButton(self.translate("SUPPORT_ON_PATREON"))
        self.patron_button.setCursor(Qt.PointingHandCursor)
        self.patron_button.clicked.connect(
            lambda: self._open_url("https://www.patreon.com/Emy69")
        )
        card_layout.addWidget(self.patron_button)

        self.x_button = QPushButton(self.translate("FOLLOW_ON_X"))
        self.x_button.setCursor(Qt.PointingHandCursor)
        self.x_button.clicked.connect(
            lambda: self._open_url("https://x.com/dev_emy")
        )
        card_layout.addWidget(self.x_button)

        card_layout.addStretch()

        self.footer_label = QLabel(self.translate("THANK_YOU_FOR_USING_APP"))
        self.footer_label.setProperty("role", "footer")
        self.footer_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        card_layout.addWidget(self.footer_label)

        root_layout.addWidget(card)

    def _make_detail_row(self, icon_path: str, text: str):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)

        icon_label = QLabel()
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(text)
        text_label.setProperty("role", "body")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(icon_label, 0, Qt.AlignTop)
        layout.addWidget(text_label, 1)

        return row, text_label

    def _open_url(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def _load_github_data_async(self):
        self.worker_thread = QThread(self)
        self.worker = GitHubDataWorker()
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._update_github_labels)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _update_github_labels(self, created_date: str, total_downloads: int, stars: int):
        if self.date_label is not None:
            self.date_label.setText(
                f"{self.translate('RELEASE_DATE_LABEL')}: {created_date}"
            )

        if self.downloads_label is not None:
            self.downloads_label.setText(
                f"{self.translate('TOTAL_DOWNLOADS_LABEL')}: {total_downloads}"
            )

        if self.stars_button is not None:
            self.stars_button.setText(
                f"{self.translate('GITHUB_STARS_LABEL')}: {stars}"
            )

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

    def show_about(self):
        self.exec()