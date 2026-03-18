import customtkinter as ctk


class UpdateBannerBuilder:
    def __init__(self, app):
        self.app = app

    def build(self):
        self.app.update_alert_frame = ctk.CTkFrame(self.app, fg_color="#4CAF50", corner_radius=0)
        self.app.update_alert_frame.pack(side="top", fill="x")
        self.app.update_alert_frame.pack_forget()

        self.app.update_alert_label = ctk.CTkLabel(
            self.app.update_alert_frame,
            text="",
            text_color="white",
            font=("Arial", 12, "bold")
        )
        self.app.update_alert_label.pack(side="left", padx=10, pady=5)

        self.app.update_download_button = ctk.CTkButton(
            self.app.update_alert_frame,
            text=self.app.tr("Download Now"),
            command=self.app.open_latest_release,
            fg_color="#388E3C",
            hover_color="#2E7D32"
        )
        self.app.update_download_button.pack(side="right", padx=10, pady=5)