import tkinter as tk
import customtkinter as ctk


class LogPanelBuilder:
    def __init__(self, app):
        self.app = app

    def build(self):
        self.app.log_textbox = ctk.CTkTextbox(self.app, width=590, height=200)
        self.app.log_textbox.pack(pady=(10, 0), padx=20, fill="both", expand=True)
        self.app.log_textbox.configure(state="disabled")

        self.app.progress_frame = ctk.CTkFrame(self.app)
        self.app.progress_frame.pack(pady=(0, 10), fill="x", padx=20)

        self.app.progress_bar = ctk.CTkProgressBar(self.app.progress_frame)
        self.app.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.app.progress_percentage = ctk.CTkLabel(self.app.progress_frame, text="0%")
        self.app.progress_percentage.pack(side="left")

        self.app.download_icon = self.app.load_and_resize_image(
            "resources/img/iconos/ui/download_icon.png", (24, 24)
        )
        self.app.toggle_details_button = ctk.CTkLabel(
            self.app.progress_frame,
            image=self.app.download_icon,
            text="",
            cursor="hand2"
        )
        self.app.toggle_details_button.pack(side="left", padx=(5, 0))
        self.app.toggle_details_button.bind("<Button-1>", lambda e: self.app.toggle_progress_details())
        self.app.toggle_details_button.bind(
            "<Enter>", lambda e: self.app.toggle_details_button.configure(fg_color="gray25")
        )
        self.app.toggle_details_button.bind(
            "<Leave>", lambda e: self.app.toggle_details_button.configure(fg_color="transparent")
        )

        self.app.progress_details_frame = ctk.CTkFrame(self.app)
        self.app.progress_details_frame.place_forget()

        self.app.context_menu = tk.Menu(self.app.url_entry, tearoff=0)
        self.app.context_menu.add_command(label=self.app.tr("Copiar"), command=self.app.copy_to_clipboard)
        self.app.context_menu.add_command(label=self.app.tr("Pegar"), command=self.app.paste_from_clipboard)
        self.app.context_menu.add_command(label=self.app.tr("Cortar"), command=self.app.cut_to_clipboard)

        self.app.url_entry.bind("<Button-3>", self.app.show_context_menu)
        self.app.bind("<Button-1>", self.app.on_click)