from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QAbstractItemView,
    QPushButton,
    QCheckBox,
    QSizePolicy,
    QToolButton,
)


class QueueItemRow(QWidget):
    """Row for the profile queue: status text plus a small remove button."""

    def __init__(self, text, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 4, 3)
        layout.setSpacing(6)

        self.text_label = QLabel(text)
        # Long URLs clip instead of widening the row or adding a
        # horizontal scrollbar.
        self.text_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.text_label, 1)

        self.remove_button = QToolButton()
        self.remove_button.setText("✕")
        self.remove_button.setAutoRaise(True)
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setFixedSize(24, 24)
        layout.addWidget(self.remove_button, 0)


class DownloadPanel(QWidget):
    def __init__(self, parent=None, tr=None):
        super().__init__(parent)
        self.tr = tr if tr else (lambda key, **kwargs: key.format(**kwargs) if kwargs else key)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.url_label = QLabel(self.tr("DOWNLOAD_PANEL_URL_LABEL"))
        root.addWidget(self.url_label)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.tr("DOWNLOAD_PANEL_URL_PLACEHOLDER"))
        url_row.addWidget(self.url_input, 1)

        self.add_to_list_button = QPushButton(self.tr("ADD_TO_LIST_SHORT"))
        self.add_to_list_button.setToolTip(self.tr("ADD_TO_LIST"))
        url_row.addWidget(self.add_to_list_button)

        self.browse_button = QPushButton(self.tr("DOWNLOAD_PANEL_SELECT_FOLDER"))
        url_row.addWidget(self.browse_button)
        root.addLayout(url_row)

        self.folder_label = QLabel("")
        self.folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.folder_label)

        # Profile queue: hidden while empty so the single-URL flow looks
        # exactly like it always has. Its height is set to the row
        # content by the main window, so it grows one row at a time.
        self.queue_list = QListWidget()
        self.queue_list.setVisible(False)
        self.queue_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.queue_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(self.queue_list)

        options_row = QHBoxLayout()

        self.images_check = QCheckBox(self.tr("DOWNLOAD_PANEL_DOWNLOAD_IMAGES"))
        self.images_check.setChecked(True)
        options_row.addWidget(self.images_check)

        self.videos_check = QCheckBox(self.tr("DOWNLOAD_PANEL_DOWNLOAD_VIDEOS"))
        self.videos_check.setChecked(True)
        options_row.addWidget(self.videos_check)

        self.compressed_check = QCheckBox(self.tr("DOWNLOAD_PANEL_DOWNLOAD_COMPRESSED"))
        self.compressed_check.setChecked(True)
        options_row.addWidget(self.compressed_check)

        options_row.addStretch(1)

        self.only_this_url_check = QCheckBox(self.tr("DOWNLOAD_PANEL_ONLY_THIS_URL"))
        self.only_this_url_check.setChecked(False)
        self.only_this_url_check.setToolTip(
            self.tr("DOWNLOAD_PANEL_ONLY_THIS_URL_TOOLTIP")
        )
        options_row.addWidget(self.only_this_url_check)

        self.autoscroll_log_check = QCheckBox(self.tr("DOWNLOAD_PANEL_AUTOSCROLL_LOG"))
        self.autoscroll_log_check.setChecked(True)
        options_row.addWidget(self.autoscroll_log_check)

        root.addLayout(options_row)

        buttons_row = QHBoxLayout()
        self.download_button = QPushButton(self.tr("DOWNLOAD_PANEL_DOWNLOAD"))
        buttons_row.addWidget(self.download_button)

        self.cancel_button = QPushButton(self.tr("DOWNLOAD_PANEL_CANCEL_DOWNLOAD"))
        self.cancel_button.setEnabled(False)
        buttons_row.addWidget(self.cancel_button)

        buttons_row.addStretch(1)
        root.addLayout(buttons_row)

    def retranslate_ui(self):
        self.url_label.setText(self.tr("DOWNLOAD_PANEL_URL_LABEL"))
        self.url_input.setPlaceholderText(self.tr("DOWNLOAD_PANEL_URL_PLACEHOLDER"))
        self.add_to_list_button.setText(self.tr("ADD_TO_LIST_SHORT"))
        self.add_to_list_button.setToolTip(self.tr("ADD_TO_LIST"))
        self.browse_button.setText(self.tr("DOWNLOAD_PANEL_SELECT_FOLDER"))
        self.images_check.setText(self.tr("DOWNLOAD_PANEL_DOWNLOAD_IMAGES"))
        self.videos_check.setText(self.tr("DOWNLOAD_PANEL_DOWNLOAD_VIDEOS"))
        self.compressed_check.setText(self.tr("DOWNLOAD_PANEL_DOWNLOAD_COMPRESSED"))
        self.only_this_url_check.setText(self.tr("DOWNLOAD_PANEL_ONLY_THIS_URL"))
        self.only_this_url_check.setToolTip(self.tr("DOWNLOAD_PANEL_ONLY_THIS_URL_TOOLTIP"))
        self.autoscroll_log_check.setText(self.tr("DOWNLOAD_PANEL_AUTOSCROLL_LOG"))
        self.download_button.setText(self.tr("DOWNLOAD_PANEL_DOWNLOAD"))
        self.cancel_button.setText(self.tr("DOWNLOAD_PANEL_CANCEL_DOWNLOAD"))
