from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar, QLabel, QHBoxLayout


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        root.addWidget(self.log_text, 1)

        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1f1f1f;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 8px;
            }
        """)
        progress_row.addWidget(self.progress_bar, 1)

        self.progress_label = QLabel("0%")
        progress_row.addWidget(self.progress_label)

        root.addLayout(progress_row)