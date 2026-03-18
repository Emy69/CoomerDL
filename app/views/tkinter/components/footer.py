import customtkinter as ctk


class FooterBuilder:
    def __init__(self, app):
        self.app = app

    def build(self):
        footer = ctk.CTkFrame(self.app, height=30, corner_radius=0)
        footer.pack(side="bottom", fill="x")

        self.app.footer_eta_label = ctk.CTkLabel(footer, text="ETA: N/A", font=("Arial", 11))
        self.app.footer_eta_label.pack(side="left", padx=20)

        self.app.footer_speed_label = ctk.CTkLabel(footer, text="Speed: 0 KB/s", font=("Arial", 11))
        self.app.footer_speed_label.pack(side="right", padx=20)