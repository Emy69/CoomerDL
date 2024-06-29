from tkinter import messagebox
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import webbrowser
import requests 

class SettingsWindow:
    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func, version):
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func
        self.version = version  # Guardar la versión como un atributo de la instancia
        self.languages = {
            "Español": "es",
            "English": "en",
            "日本語": "ja",
            "中文": "zh",
            "Français": "fr",
            "Português": "pt",
            "Русский": "ru"
        }

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

        compatible_label = ctk.CTkLabel(self.content_frame, text=self.translate("Compatible con:"), font=("Helvetica", 16, "bold"))
        compatible_label.pack(pady=20)

        self.site_logos = {
            "Erome": "resources/img/logos/erome_logo.png",
            "Bunkr": "resources/img/logos/bunkr_logo.png",
            "Coomer.su": "resources/img/logos/coomer_logo.png",
            "Kemono.su": "resources/img/logos/kemono_logo.png",
        }

        for site, logo_path in self.site_logos.items():
            site_frame = ctk.CTkFrame(self.content_frame)
            site_frame.pack(fill='x', padx=20, pady=10)

            logo_image = self.create_photoimage(logo_path, size=(50, 50))
            logo_label = tk.Label(site_frame, image=logo_image, bg="white")
            logo_label.image = logo_image
            logo_label.pack(side='left', padx=10)
            
            site_label = ctk.CTkLabel(site_frame, text=site, font=("Helvetica", 14))
            site_label.pack(side='left', padx=10)


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

