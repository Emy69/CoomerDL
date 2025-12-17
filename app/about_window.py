import threading
import customtkinter as ctk
import webbrowser
import requests
from PIL import Image

class AboutWindow:
    def __init__(self, parent, translate, version):
        self.parent = parent
        self.translate = translate
        self.version = version

    def get_github_data(self):
        url = "https://api.github.com/repos/Emy69/CoomerDL"
        try:
            response = requests.get(url)
            response.raise_for_status()
            repo_data = response.json()

            # Obtener la fecha de creación y las descargas totales (si existen releases)
            created_at = repo_data.get("created_at", "N/A")
            created_date = created_at.split("T")[0] if created_at != "N/A" else "N/A"

            releases_url = repo_data.get("releases_url", "").replace("{/id}", "")
            releases_response = requests.get(releases_url)
            releases_response.raise_for_status()
            releases_data = releases_response.json()

            total_downloads = sum(
                asset["download_count"] for release in releases_data for asset in release.get("assets", [])
            ) if releases_data else 0

            return created_date, total_downloads
        except Exception as e:
            print(f"Error fetching GitHub data: {e}")
            return "N/A", 0

    def show_about(self):
        # Crear una nueva ventana
        about_window = ctk.CTkToplevel(self.parent)
        about_window.title(self.translate("About"))
        about_window.geometry("300x600")
        about_window.resizable(False, False)

        # Centrar la ventana
        self.center_window(about_window, 300, 600)

        # Hacer que la ventana aparezca al frente
        about_window.transient(self.parent)
        about_window.lift()
        about_window.grab_set()

        # placeholders mientras carga
        created_date = self.translate("Loading...")
        total_downloads = self.translate("Loading...")

        # Crear un marco para el contenido
        about_frame = ctk.CTkFrame(about_window, corner_radius=15)
        about_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Encabezado estilizado
        header_label = ctk.CTkLabel(
            about_frame,
            text=self.translate("About This App"), 
            font=("Helvetica", 20, "bold"),
            text_color="white",
            anchor="w" 
        )
        header_label.pack(pady=(10, 5), padx=10, anchor="w") 

        # Cargar las imágenes de los íconos
        developer_icon = ctk.CTkImage(Image.open("resources/img/iconos/about/user-account-solid-24.png"), size=(20, 20))
        version_icon = ctk.CTkImage(Image.open("resources/img/iconos/about/git-branch-line.png"), size=(20, 20))
        downloads_icon = ctk.CTkImage(Image.open("resources/img/iconos/about/download_icon.png"), size=(20, 20))
        date_icon = ctk.CTkImage(Image.open("resources/img/iconos/about/calendar-event-line.png"), size=(20, 20))

        # labels que se actualizarán
        self.downloads_label = None
        self.date_label = None

        details = [
            (developer_icon, f"{self.translate('Developer')}: Emy69", None),
            (version_icon, f"{self.translate('Version')}: {self.version}", None),
            (downloads_icon, f"{self.translate('Total Downloads')}: {total_downloads}", "downloads"),
            (date_icon, f"{self.translate('Release Date')}: {created_date}", "date")
        ]

        for icon, text, key in details:
            detail_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
            detail_frame.pack(anchor="w", pady=5, padx=30)

            icon_label = ctk.CTkLabel(detail_frame, text="", image=icon)
            icon_label.pack(side="left", padx=(0, 10))

            text_label = ctk.CTkLabel(
                detail_frame,
                text=text,
                font=("Helvetica", 14),
                text_color="white",
                justify="left"
            )
            text_label.pack(side="left")

            if key == "downloads":   # agregado
                self.downloads_label = text_label
            elif key == "date":      # agregado
                self.date_label = text_label

        separator = ctk.CTkFrame(about_frame, height=1, fg_color="gray")
        separator.pack(fill="x", padx=10, pady=10)

        # Sección de plataformas soportadas
        supported_label = ctk.CTkLabel(
            about_frame, 
            text=self.translate("Supported Platforms"), 
            font=("Helvetica", 16, "bold"),
            text_color="white",
            anchor="w"
        )
        supported_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Lista de plataformas con íconos
        platforms = [
            ("coomer.su", "https://coomer.su"),
            ("kemono.su", "https://kemono.su"),
            ("erome.com", "https://erome.com"),
            ("bunkr-albums.io", "https://bunkr-albums.io"),
            ("simpcity.su", "https://simpcity.su"),
            ("jpg5.su", "https://jpg5.su")
        ]

        for name, url in platforms:
            # Crear el marco para cada plataforma
            platform_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
            platform_frame.pack(anchor="w", pady=5, padx=10)

            icon_image = ctk.CTkImage(Image.open("resources/img/iconos/about/global-line.png"), size=(20, 20))
            icon_label = ctk.CTkLabel(platform_frame, text="", image=icon_image)
            icon_label.pack(side="left")

            # Botón con el nombre de la plataforma
            platform_button = ctk.CTkButton(
                platform_frame,
                text=name,
                font=("Helvetica", 14),
                fg_color="transparent",
                hover_color="gray25",
                command=lambda u=url: webbrowser.open(u)
            )
            platform_button.pack(side="left")

        # Footer
        footer_label = ctk.CTkLabel(
            about_frame, 
            text=self.translate("Thank you for using our app!"), 
            font=("Helvetica", 12, "italic"), 
            text_color="white",
            anchor="w"
        )
        footer_label.pack(pady=(10, 10), padx=10, anchor="w")

        # hilo para cargar datos
        def fetch_and_update():
            cd, td = self.get_github_data()

            def safe_update():
                try:
                    if not about_window.winfo_exists():
                        return
                    if self.date_label and self.date_label.winfo_exists():
                        self.date_label.configure(text=f"{self.translate('Release Date')}: {cd}")
                    if self.downloads_label and self.downloads_label.winfo_exists():
                        self.downloads_label.configure(text=f"{self.translate('Total Downloads')}: {td}")
                except Exception:
                    pass

            about_window.after(0, safe_update)
        threading.Thread(target=fetch_and_update, daemon=True).start()



    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')