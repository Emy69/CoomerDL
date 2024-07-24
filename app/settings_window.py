import json
import os
from tkinter import messagebox
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import webbrowser
import requests 

class SettingsWindow:
    CONFIG_PATH = 'resources/config/settings.json'

    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func, version):
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func
        self.version = version
        self.languages = {
            "Español": "es",
            "English": "en",
            "日本語": "ja",
            "中文": "zh",
            "Français": "fr",
            "Русский": "ru"
        }

        self.settings = self.load_settings()
    
    def load_settings(self):
        if not os.path.exists(self.CONFIG_PATH):
            return {'max_downloads': 3}  # Valor predeterminado

        try:
            with open(self.CONFIG_PATH, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'max_downloads': 3}  # Valor predeterminado

    def save_settings(self):
        os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
        with open(self.CONFIG_PATH, 'w') as file:
            json.dump(self.settings, file)

    def open_settings(self):
        self.settings_window = ctk.CTkToplevel(self.parent)
        self.settings_window.title(self.translate("Configuraciones"))
        self.settings_window.geometry("800x600")
        self.settings_window.transient(self.parent)
        self.settings_window.grab_set()
        self.center_window(self.settings_window, 800, 600)
        self.settings_window.resizable(False, False)  # Hacer que la ventana no se pueda redimensionar

        # Crear la barra de navegación
        nav_frame = ctk.CTkFrame(self.settings_window, width=200)
        nav_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Crear el marco de contenido
        self.content_frame = ctk.CTkFrame(self.settings_window)
        self.content_frame.pack(side="right", expand=True, fill="both", padx=(10, 20), pady=10)

        # Añadir botones de navegación
        self.create_nav_button(nav_frame, "Idioma", self.show_language_settings)
        self.create_nav_button(nav_frame, "Buscar actualizaciones", self.show_update_settings)
        self.create_nav_button(nav_frame, "Descargas", self.show_download_settings)
        self.create_nav_button(nav_frame, "Acerca de", self.show_about)

    def create_nav_button(self, parent, text, command):
        button = ctk.CTkButton(parent, text=self.translate(text), command=command)
        button.pack(pady=5, fill='x')

    def show_language_settings(self):
        self.clear_frame(self.content_frame)

        language_label = ctk.CTkLabel(self.content_frame, text=self.translate("Selecciona idioma"), font=("Helvetica", 16, "bold"))
        language_label.pack(pady=10)

        language_combobox = ctk.CTkComboBox(self.content_frame, values=list(self.languages.keys()), state='readonly')
        language_combobox.pack(pady=10)

        apply_button = ctk.CTkButton(self.content_frame, text=self.translate("Aplicar"), command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_button.pack(pady=10)

    def show_download_settings(self):
        self.clear_frame(self.content_frame)

        download_label = ctk.CTkLabel(self.content_frame, text=self.translate("Opciones de Descarga"), font=("Helvetica", 16, "bold"))
        download_label.pack(pady=10)

        max_downloads_label = ctk.CTkLabel(self.content_frame, text=self.translate("Descargas Simultáneas"))
        max_downloads_label.pack(pady=10)

        self.max_downloads_combobox = ctk.CTkComboBox(self.content_frame, values=[str(i) for i in range(1, 11)], state='readonly')
        self.max_downloads_combobox.set(str(self.settings.get('max_downloads', 3)))
        self.max_downloads_combobox.pack(pady=10)

        apply_button = ctk.CTkButton(self.content_frame, text=self.translate("Aplicar"), command=self.apply_download_settings)
        apply_button.pack(pady=10)

        # Obtener el ancho de la pantalla
        screen_width = self.content_frame.winfo_screenwidth()

        # Calcular el ancho máximo permitido para el label (por ejemplo, 80% del ancho de la pantalla)
        max_label_width = int(screen_width * 0.8)

        # Agregar mensaje de advertencia con ancho máximo
        warning_label = ctk.CTkLabel(self.content_frame, text=self.translate("Para Coomer y Kemono, se recomienda un máximo de 3-5 descargas simultáneas para evitar errores 429."), font=("Helvetica", 12, "italic"), text_color="yellow", wraplength=max_label_width)
        warning_label.pack(pady=10)

    def apply_download_settings(self):
        max_downloads = int(self.max_downloads_combobox.get())
        self.settings['max_downloads'] = max_downloads
        self.save_settings()
        self.parent.update_max_downloads(max_downloads)
        messagebox.showinfo(self.translate("Configuraciones"), self.translate("Configuraciones de descarga actualizadas"))

    def show_general_settings(self):
        self.clear_frame(self.content_frame)

        general_label = ctk.CTkLabel(self.content_frame, text=self.translate("Opciones Generales"), font=("Helvetica", 16, "bold"))
        general_label.pack(pady=10)

    def show_update_settings(self):
        self.clear_frame(self.content_frame)

        update_label = ctk.CTkLabel(self.content_frame, text=self.translate("Buscar actualizaciones"), font=("Helvetica", 16, "bold"))
        update_label.pack(pady=10)

        update_button = ctk.CTkButton(self.content_frame, text=self.translate("Buscar"), command=self.check_for_updates)
        update_button.pack(pady=10)

    def show_about(self):
        self.clear_frame(self.content_frame)

        about_label = ctk.CTkLabel(self.content_frame, text=self.translate("Acerca de"), font=("Helvetica", 20, "bold"))
        about_label.pack(pady=20)

        description_text = f"""
        {self.translate("Desarrollado por: Emy69")}

        {self.translate("Versión")}: {self.version}

        {self.translate("Repositorio")}: 
        """
        description_label = ctk.CTkLabel(self.content_frame, text=description_text, font=("Helvetica", 14))
        description_label.pack(pady=10)

        repo_link = ctk.CTkButton(self.content_frame, text="GitHub: Emy69/CoomerDL", command=lambda: webbrowser.open("https://github.com/Emy69/CoomerDL"))
        repo_link.pack(pady=10)

        contributors_label = ctk.CTkLabel(self.content_frame, text=self.translate("Contribuidores"), font=("Helvetica", 16, "bold"))
        contributors_label.pack(pady=20)

        self.show_contributors()

    def apply_language_settings(self, selected_language_name):
        selected_language_code = self.languages[selected_language_name]
        self.save_language_preference(selected_language_code)
        self.load_translations(selected_language_code)
        self.update_ui_texts()

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def create_photoimage(self, path, size=(32, 32)):
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)
        photoimg = ImageTk.PhotoImage(img)
        return photoimg

    def update_all_widgets(self, widget):
        for child in widget.winfo_children():
            if isinstance(child, (ctk.CTkFrame, ctk.CTkButton, ctk.CTkLabel, ctk.CTkComboBox)):
                child.update()
            self.update_all_widgets(child)

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def check_for_updates(self):
        api_url = "https://api.github.com/repos/Emy69/CoomerDL/releases/latest"

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release["tag_name"].lstrip('v')  # Remover prefijo 'v' si existe

            if latest_version != self.version.lstrip('v'):
                if messagebox.askyesno(self.translate("Actualización disponible"),
                                       self.translate(f"Hay una nueva versión disponible: {latest_version}\n"
                                                      "¿Deseas ir a la página de descargas?")):
                    webbrowser.open("https://github.com/Emy69/CoomerDL/releases")
            else:
                messagebox.showinfo(self.translate("Actualización"),
                                    self.translate("Tu software está actualizado."))
        except requests.RequestException as e:
            messagebox.showerror(self.translate("Error"),
                                 self.translate(f"No se pudo verificar si hay actualizaciones.\nError: {e}"))

    def show_contributors(self):
        try:
            response = requests.get("https://api.github.com/repos/Emy69/CoomerDL/contributors")
            response.raise_for_status()
            contributors = response.json()

            for contributor in contributors:
                frame = ctk.CTkFrame(self.content_frame)
                frame.pack(fill='x', padx=20, pady=10)

                avatar_url = contributor["avatar_url"]
                avatar_image = Image.open(requests.get(avatar_url, stream=True).raw)
                avatar_image = avatar_image.resize((50, 50), Image.Resampling.LANCZOS)
                avatar_photo = ImageTk.PhotoImage(avatar_image)

                avatar_label = tk.Label(frame, image=avatar_photo)
                avatar_label.image = avatar_photo
                avatar_label.pack(side="left", padx=10)

                name_label = ctk.CTkLabel(frame, text=contributor["login"], font=("Helvetica", 14))
                name_label.pack(side="left", padx=10)

                link_button = ctk.CTkButton(frame, text=self.translate("Perfil"), command=lambda url=contributor["html_url"]: webbrowser.open(url))
                link_button.pack(side="left", padx=10)

        except requests.RequestException as e:
            messagebox.showerror(self.translate("Error"), self.translate(f"No se pudieron cargar los contribuidores.\nError: {e}"))
