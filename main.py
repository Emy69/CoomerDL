import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.views.pyside.main_window import PySideMainWindow


def main():
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)

    app_icon = QIcon("resources/img/icono.ico")
    app.setWindowIcon(app_icon)
    
    window = PySideMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()