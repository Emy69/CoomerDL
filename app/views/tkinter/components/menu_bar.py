import webbrowser
import customtkinter as ctk
from PIL import Image


class MenuBarBuilder:
    def __init__(self, app):
        self.app = app

    def build(self):
        self.app.menu_bar = ctk.CTkFrame(self.app, height=30, corner_radius=0)
        self.app.menu_bar.pack(side="top", fill="x")

        archivo_button = ctk.CTkButton(
            self.app.menu_bar,
            text=self.app.tr("Archivo"),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=self.app.toggle_archivo_menu
        )
        archivo_button.pack(side="left")
        archivo_button.bind("<Button-1>", lambda e: "break")

        about_button = ctk.CTkButton(
            self.app.menu_bar,
            text=self.app.tr("About"),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=self.app.about_window.show_about
        )
        about_button.pack(side="left")
        about_button.bind("<Button-1>", lambda e: "break")

        donors_button = ctk.CTkButton(
            self.app.menu_bar,
            text=self.app.tr("Patreons"),
            width=80,
            fg_color="transparent",
            hover_color="gray25",
            command=self.app.show_donors_modal
        )
        donors_button.pack(side="left")
        donors_button.bind("<Button-1>", lambda e: "break")

        self.app.archivo_menu_frame = None
        self.app.ayuda_menu_frame = None
        self.app.donaciones_menu_frame = None

        def on_enter(event, frame):
            frame.configure(fg_color="gray25")

        def on_leave(event, frame):
            frame.configure(fg_color="transparent")

        if self.app.github_icon:
            resized_github_icon = self.app.github_icon.resize((16, 16), Image.Resampling.LANCZOS)
            resized_github_icon = ctk.CTkImage(resized_github_icon)

            github_frame = ctk.CTkFrame(self.app.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            github_frame.pack(side="right", padx=5)

            github_label = ctk.CTkLabel(
                github_frame,
                image=resized_github_icon,
                text=f" Star {self.app.github_stars}",
                compound="left",
                font=("Arial", 12)
            )
            github_label.pack(padx=5, pady=5)

            github_frame.bind("<Enter>", lambda e: on_enter(e, github_frame))
            github_frame.bind("<Leave>", lambda e: on_leave(e, github_frame))
            github_label.bind("<Enter>", lambda e: on_enter(e, github_frame))
            github_label.bind("<Leave>", lambda e: on_leave(e, github_frame))
            github_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/emy69/CoomerDL"))

        self.app.discord_icon = self.app.load_discord_icon()
        if self.app.discord_icon:
            resized_discord_icon = self.app.discord_icon.resize((16, 16), Image.Resampling.LANCZOS)
            resized_discord_icon = ctk.CTkImage(resized_discord_icon)

            discord_frame = ctk.CTkFrame(self.app.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            discord_frame.pack(side="right", padx=5)

            discord_label = ctk.CTkLabel(
                discord_frame,
                image=resized_discord_icon,
                text="Discord",
                compound="left"
            )
            discord_label.pack(padx=5, pady=5)

            discord_frame.bind("<Enter>", lambda e: on_enter(e, discord_frame))
            discord_frame.bind("<Leave>", lambda e: on_leave(e, discord_frame))
            discord_label.bind("<Enter>", lambda e: on_enter(e, discord_frame))
            discord_label.bind("<Leave>", lambda e: on_leave(e, discord_frame))
            discord_label.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/ku8gSPsesh"))

        self.app.new_icon = self.app.load_patreon_icon()
        if self.app.new_icon:
            resized_new_icon = self.app.new_icon.resize((16, 16), Image.Resampling.LANCZOS)
            resized_new_icon = ctk.CTkImage(resized_new_icon)

            new_icon_frame = ctk.CTkFrame(self.app.menu_bar, cursor="hand2", fg_color="transparent", corner_radius=5)
            new_icon_frame.pack(side="right", padx=5)

            new_icon_label = ctk.CTkLabel(
                new_icon_frame,
                image=resized_new_icon,
                text="Patreon",
                compound="left"
            )
            new_icon_label.pack(padx=5, pady=5)

            new_icon_frame.bind("<Enter>", lambda e: on_enter(e, new_icon_frame))
            new_icon_frame.bind("<Leave>", lambda e: on_leave(e, new_icon_frame))
            new_icon_label.bind("<Enter>", lambda e: on_enter(e, new_icon_frame))
            new_icon_label.bind("<Leave>", lambda e: on_leave(e, new_icon_frame))
            new_icon_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.patreon.com/Emy69"))