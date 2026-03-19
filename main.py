import sys
from PySide6.QtWidgets import QApplication

from app.views.pyside.main_window import PySideMainWindow


def main():
    app = QApplication(sys.argv)
    window = PySideMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()