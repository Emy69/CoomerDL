from PySide6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QLabel


class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Progress Details")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        self.empty_label = QLabel("No active downloads")
        layout.addWidget(self.empty_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll, 1)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 8, 8, 8)
        self.container_layout.setSpacing(8)
        self.container_layout.addStretch(1)

        self.scroll.setWidget(self.container)

    def show_empty(self, visible: bool):
        self.empty_label.setVisible(visible)