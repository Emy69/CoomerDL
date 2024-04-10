import tkinter as tk
from customtkinter import CTkToplevel, CTkLabel, CTkCheckBox, CTkButton

class PatchNotes:
    def __init__(self, parent, translations_func):
        self.parent = parent
        self.tr = translations_func

    def show_patch_notes(self, auto_show=False):
        if auto_show and not self.should_show_patch_notes():
            return

        patch_notes_window = CTkToplevel(self.parent)
        patch_notes_window.title(self.tr("Notas de Parche"))
        window_width = 1000
        window_height = 300

        position_right = int(self.parent.winfo_x() + (self.parent.winfo_width() / 2) - (window_width / 2))
        position_down = int(self.parent.winfo_y() + (self.parent.winfo_height() / 2) - (window_height / 2))

        patch_notes_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")

        patch_notes_window.transient(self.parent)
        patch_notes_window.grab_set()

        patch_notes_text = self.tr("patch_notes_text")
        patch_notes_content = CTkLabel(patch_notes_window, text=patch_notes_text, justify="left")
        patch_notes_content.pack(pady=10, padx=10)

        dont_show_again_var = tk.IntVar(value=0)
        dont_show_again_check = CTkCheckBox(patch_notes_window, text=self.tr("No_mostrar"), variable=dont_show_again_var)
        dont_show_again_check.pack()

        ok_button = CTkButton(patch_notes_window, text=self.tr("OK"), command=lambda: self.close_patch_notes(patch_notes_window, dont_show_again_var))
        ok_button.pack(pady=10)
    
    def close_patch_notes(self, window, dont_show_again_var):
        # Guarda la preferencia del usuario
        self.save_patch_notes_preference(not bool(dont_show_again_var.get()))
        window.destroy()
    
    def save_patch_notes_preference(self, show_again):
        with open("resources/config/patch_notes/patch_notes_pref.txt", "w") as f:
            f.write(str(show_again))

    def should_show_patch_notes(self):
        try:
            with open("resources/config/patch_notes/patch_notes_pref.txt", "r") as f:
                return f.read().strip().lower() in ['true', '1', 't', 'y', 'yes']
        except FileNotFoundError:
            return True