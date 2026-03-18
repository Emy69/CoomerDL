import os
import subprocess
import sys
from tkinter import messagebox


class UIHelpers:
    def __init__(self, app):
        self.app = app

    def on_hover_enter(self, event=None):
        self.app.folder_path.configure(font=("Arial", 13, "underline"))

    def on_hover_leave(self, event=None):
        self.app.folder_path.configure(font=("Arial", 13))

    def open_download_folder(self, event=None):
        if self.app.download_folder and os.path.exists(self.app.download_folder):
            if sys.platform == "win32":
                os.startfile(self.app.download_folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.app.download_folder])
            else:
                subprocess.Popen(["xdg-open", self.app.download_folder])
        else:
            messagebox.showerror(
                self.app.tr("Error"),
                self.app.tr("La carpeta no existe o no es válida.")
            )