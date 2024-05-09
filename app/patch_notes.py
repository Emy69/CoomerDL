import tkinter as tk
from customtkinter import CTkToplevel, CTkLabel, CTkCheckBox, CTkButton
import os

class PatchNotes:
    WINDOW_WIDTH = 950
    WINDOW_HEIGHT = 450
    PATCH_NOTES_PATH = "resources/config/patch_notes/patch_notes_pref.txt"

    def __init__(self, parent, translations_func):
        self.parent = parent
        self.tr = translations_func

    def show_patch_notes(self, auto_show=False):
        if auto_show and not self.should_show_patch_notes():
            return

        patch_notes_window = CTkToplevel(self.parent)
        patch_notes_window.title(self.tr("Notas de Parche"))
        self.configure_window_geometry(patch_notes_window)

        patch_notes_window.transient(self.parent)
        patch_notes_window.grab_set()

        patch_notes_text = self.get_patch_notes_text()
        patch_notes_content = CTkLabel(patch_notes_window, text=patch_notes_text, justify="left")
        patch_notes_content.pack(pady=10, padx=10)

        dont_show_again_var = tk.IntVar(value=0)
        dont_show_again_check = CTkCheckBox(patch_notes_window, text=self.tr("No_mostrar"), variable=dont_show_again_var)
        dont_show_again_check.pack()

        ok_button = CTkButton(patch_notes_window, text=self.tr("OK"), command=lambda: self.close_patch_notes(patch_notes_window, dont_show_again_var))
        ok_button.pack(pady=10)
    
    def configure_window_geometry(self, window):
        position_right = int(self.parent.winfo_x() + (self.parent.winfo_width() / 2) - (self.WINDOW_WIDTH / 2))
        position_down = int(self.parent.winfo_y() + (self.parent.winfo_height() / 2) - (self.WINDOW_HEIGHT / 2))
        window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{position_right}+{position_down}")

    def get_patch_notes_text(self):
        return """
            Patch Notes 0.5.5:\n
            - change of logos 

            """

    def close_patch_notes(self, window, dont_show_again_var):
        self.save_patch_notes_preference(not bool(dont_show_again_var.get()))
        window.destroy()
    
    def save_patch_notes_preference(self, show_again):
        os.makedirs(os.path.dirname(self.PATCH_NOTES_PATH), exist_ok=True)
        with open(self.PATCH_NOTES_PATH, "w") as f:
            f.write(str(show_again))

    def should_show_patch_notes(self):
        try:
            with open(self.PATCH_NOTES_PATH, "r") as f:
                return f.read().strip().lower() in ['true', '1', 't', 'y', 'yes']
        except Exception as e:
            print(f"Error reading patch notes preferences: {e}")
            return True
