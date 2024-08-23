import tkinter as tk
import requests
from tkinterweb import HtmlFrame
import customtkinter as ctk
import markdown2

class PatchNotes:
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 800

    def __init__(self, parent, translations_func):
        self.parent = parent
        self.tr = translations_func
        self.patch_notes_window = None

    def show_patch_notes(self):
        if self.patch_notes_window is not None and tk.Toplevel.winfo_exists(self.patch_notes_window):
            self.patch_notes_window.lift()
            return
        
        self.patch_notes_window = ctk.CTkToplevel(self.parent)
        self.patch_notes_window.title(self.tr("Patch Notes"))
        self.patch_notes_window.transient(self.parent)
        self.patch_notes_window.grab_set()
        
        self.center_window(self.patch_notes_window, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        main_frame = ctk.CTkFrame(self.patch_notes_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Obtener el release más reciente desde GitHub
        latest_release = self.get_latest_github_release('Emy69', 'CoomerDL')
        
        # Crear un HtmlFrame para mostrar el contenido HTML
        html_frame = HtmlFrame(main_frame, messages_enabled=False)
        html_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Cargar el contenido HTML
        if latest_release:
            patch_notes_html = self.get_patch_notes_html(latest_release)
            html_frame.load_html(patch_notes_html)
        else:
            html_frame.load_html("<p>Failed to load patch notes.</p>")

        # Añadir un frame inferior para el botón y opción de "No mostrar de nuevo"
        bottom_frame = ctk.CTkFrame(self.patch_notes_window)
        bottom_frame.pack(fill="x", padx=20, pady=(0, 20))

        dont_show_again_var = tk.IntVar()
        dont_show_again_check = ctk.CTkCheckBox(bottom_frame, text=self.tr("Don't show again"), variable=dont_show_again_var)
        dont_show_again_check.pack(side="left", padx=5)

        ok_button = ctk.CTkButton(bottom_frame, text=self.tr("OK"), command=lambda: self.close_patch_notes(dont_show_again_var))
        ok_button.pack(side="right", padx=5)

    @staticmethod
    def get_latest_github_release(repo_owner, repo_name):
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def get_patch_notes_html(self, latest_release):
        # Convertir el cuerpo del release de Markdown a HTML
        release_body_html = markdown2.markdown(latest_release['body'])

        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    background-color: #1e1e1e;
                    color: #f5f5f5;
                    padding: 20px;
                    margin: 0;
                }}
                h1 {{
                    color: #ffcc00;
                    text-align: center;
                    margin-top: 10px;
                }}
                h2 {{
                    color: #ff6600;
                    margin-bottom: 5px;
                    text-align: center;
                }}
                p {{
                    margin-bottom: 15px;
                    line-height: 1.6;
                    text-align: justify;
                }}
                .footer {{
                    text-align: center;
                    font-size: 12px;
                    color: #888;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>{self.tr('Patch Notes')}</h1>
            <h2>{latest_release['name']}</h2>
            {release_body_html}
        </body>
        </html>
        """

        return html_content

    def close_patch_notes(self, dont_show_again_var):
        if self.patch_notes_window is not None:
            self.patch_notes_window.destroy()
            self.patch_notes_window = None

