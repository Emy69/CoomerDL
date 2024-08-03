import tkinter as tk
from PIL import Image as PilImage, ImageTk
import customtkinter as ctk
import os

class PatchNotes:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 759
    IMAGE_PATH = "resources/img/image.png"

    def __init__(self, parent, translations_func):
        self.parent = parent
        self.tr = translations_func
        self.patch_notes_window = None

    def show_patch_notes(self):
        if self.patch_notes_window is not None and tk.Toplevel.winfo_exists(self.patch_notes_window):
            self.patch_notes_window.lift()
            return
        
        self.patch_notes_window = ctk.CTkToplevel(self.parent)
        self.patch_notes_window.title(self.tr("<3"))
        self.patch_notes_window.transient(self.parent)
        self.patch_notes_window.grab_set()

        self.center_window(self.patch_notes_window, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        main_frame = ctk.CTkFrame(self.patch_notes_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        patch_notes_text = self.get_patch_notes_text()
        patch_notes_content = ctk.CTkLabel(
            main_frame, 
            text=patch_notes_text, 
            justify="center", 
            wraplength=self.WINDOW_WIDTH - 40, 
            font=("Helvetica", 15)
        )
        patch_notes_content.pack(pady=(20, 10))

        self.load_image(main_frame)

        dont_show_again_var = tk.IntVar(value=0)
        ok_button = ctk.CTkButton(self.patch_notes_window, text=self.tr("OK"), command=lambda: self.close_patch_notes(dont_show_again_var))
        ok_button.pack(pady=10)

    def load_image(self, parent):
        if os.path.exists(self.IMAGE_PATH):
            try:
                pil_image = PilImage.open(self.IMAGE_PATH)
                pil_image = pil_image.resize((448, 398), PilImage.Resampling.LANCZOS)
                photo_image = ImageTk.PhotoImage(pil_image)
                
                image_label = tk.Label(parent, image=photo_image)
                image_label.image = photo_image
                image_label.pack(pady=(10, 10))
            except Exception as e:
                print(f"Error loading image: {e}")
                error_label = ctk.CTkLabel(parent, text=self.tr("No se pudo cargar la imagen."))
                error_label.pack(pady=(10, 10))
        else:
            print(f"Image file not found: {self.IMAGE_PATH}")
            error_label = ctk.CTkLabel(parent, text=self.tr("Archivo de imagen no encontrado."))
            error_label.pack(pady=(10, 10))

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def get_patch_notes_text(self):
        return self.tr("thank you for all the support")

    def close_patch_notes(self, dont_show_again_var):
        #self.save_patch_notes_preference(not bool(dont_show_again_var.get()))
        if self.patch_notes_window is not None:
            self.patch_notes_window.destroy()
            self.patch_notes_window = None