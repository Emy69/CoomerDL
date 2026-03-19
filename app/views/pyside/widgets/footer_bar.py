from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


class FooterBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.eta_label = QLabel("ETA: N/A")
        self.speed_label = QLabel("Speed: 0 KB/s")

        layout.addWidget(self.eta_label)
        layout.addStretch(1)
        layout.addWidget(self.speed_label)