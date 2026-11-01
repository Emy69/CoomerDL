import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.views.pyside.main_window import PySideMainWindow


def _app_dir():
    # Settings, translations, icons and downloads.db are all read from
    # resources/ relative to the working directory, so start from the folder
    # that holds it no matter where the app was launched from.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    os.chdir(_app_dir())
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)

    app_icon = QIcon("resources/img/icono.ico")
    app.setWindowIcon(app_icon)
    
    # The window shows itself after the startup community dialog resolves;
    # keep a reference so it isn't garbage collected.
    _window = PySideMainWindow()  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()