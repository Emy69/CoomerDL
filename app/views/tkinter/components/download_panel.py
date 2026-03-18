import tkinter as tk
import customtkinter as ctk


class DownloadPanelBuilder:
    def __init__(self, app):
        self.app = app

    def build(self):
        self.app.input_frame = ctk.CTkFrame(self.app)
        self.app.input_frame.pack(fill="x", padx=20, pady=20)
        self.app.input_frame.grid_columnconfigure(0, weight=1)
        self.app.input_frame.grid_rowconfigure(1, weight=1)

        self.app.url_label = ctk.CTkLabel(self.app.input_frame, text=self.app.tr("URL de la página web:"))
        self.app.url_label.grid(row=0, column=0, sticky="w")

        self.app.url_entry = ctk.CTkEntry(self.app.input_frame)
        self.app.url_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        self.app.browse_button = ctk.CTkButton(
            self.app.input_frame,
            text=self.app.tr("Seleccionar Carpeta"),
            command=self.app.select_folder
        )
        self.app.browse_button.grid(row=1, column=1, sticky="e")

        self.app.folder_path = ctk.CTkLabel(
            self.app.input_frame,
            text=self.app.download_folder or "",
            cursor="hand2",
            font=("Arial", 13)
        )
        self.app.folder_path.grid(row=2, column=0, columnspan=2, sticky="w")
        self.app.folder_path.bind("<Button-1>", self.app.open_download_folder)
        self.app.folder_path.bind("<Enter>", self.app.on_hover_enter)
        self.app.folder_path.bind("<Leave>", self.app.on_hover_leave)

        self.app.options_frame = ctk.CTkFrame(self.app)
        self.app.options_frame.pack(pady=10, fill="x", padx=20)

        self.app.download_images_check = ctk.CTkCheckBox(
            self.app.options_frame,
            text=self.app.tr("Descargar Imágenes")
        )
        self.app.download_images_check.pack(side="left", padx=10)
        self.app.download_images_check.select()

        self.app.download_videos_check = ctk.CTkCheckBox(
            self.app.options_frame,
            text=self.app.tr("Descargar Vídeos")
        )
        self.app.download_videos_check.pack(side="left", padx=10)
        self.app.download_videos_check.select()

        self.app.download_compressed_check = ctk.CTkCheckBox(
            self.app.options_frame,
            text=self.app.tr("Descargar Comprimidos")
        )
        self.app.download_compressed_check.pack(side="left", padx=10)
        self.app.download_compressed_check.select()

        self.app.action_frame = ctk.CTkFrame(self.app)
        self.app.action_frame.pack(pady=10, fill="x", padx=20)

        self.app.download_button = ctk.CTkButton(
            self.app.action_frame,
            text=self.app.tr("Descargar"),
            command=self.app.start_download
        )
        self.app.download_button.pack(side="left", padx=10)

        self.app.cancel_button = ctk.CTkButton(
            self.app.action_frame,
            text=self.app.tr("Cancelar Descarga"),
            state="disabled",
            command=self.app.cancel_download
        )
        self.app.cancel_button.pack(side="left", padx=10)

        self.app.autoscroll_logs_var = tk.BooleanVar(value=False)
        self.app.autoscroll_logs_checkbox = ctk.CTkCheckBox(
            self.app.action_frame,
            text=self.app.tr("Auto-scroll logs"),
            variable=self.app.autoscroll_logs_var
        )
        self.app.autoscroll_logs_checkbox.pack(side="right")

        self.app.progress_label = ctk.CTkLabel(self.app.action_frame, text="")
        self.app.progress_label.pack(side="left", padx=10)