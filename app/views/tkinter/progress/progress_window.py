import customtkinter as ctk


class ProgressWindow:
    def __init__(self, root, title="Detalles de Descarga"):
        self.root = root
        self.title = title
        self.window = None
        self.details_frame = None
        self.no_downloads_label = None

    def ensure_created(self):
        if self.window is None or not self.window.winfo_exists():
            self.window = ctk.CTkToplevel(self.root)
            self.window.title(self.title)
            self.window.geometry("600x500")
            self.window.resizable(True, True)
            self.window.protocol("WM_DELETE_WINDOW", self.close)

            self.details_frame = ctk.CTkFrame(self.window)
            self.details_frame.pack(fill="both", expand=True, padx=10, pady=10)

            self.no_downloads_label = ctk.CTkLabel(
                self.details_frame,
                text="No hay descargas en cola",
                font=("Arial", 14)
            )
            self.no_downloads_label.pack(pady=20)

            self.window.transient(self.root)
            self.window.grab_set()

    def close(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.grab_release()
            self.window.withdraw()

    def show(self):
        self.ensure_created()
        self.center()
        self.window.deiconify()
        self.window.lift()

    def is_visible(self):
        return self.window is not None and self.window.winfo_exists() and self.window.winfo_viewable()

    def center(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.update_idletasks()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.window.geometry(f"{width}x{height}+{x}+{y}")
            self.window.minsize(width, height)

    def hide_empty_message(self):
        if self.no_downloads_label and self.no_downloads_label.winfo_exists():
            self.no_downloads_label.pack_forget()

    def show_empty_message(self):
        if self.no_downloads_label and self.no_downloads_label.winfo_exists():
            self.no_downloads_label.pack(pady=20)