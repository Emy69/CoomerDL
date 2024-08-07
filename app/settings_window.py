import json
import os
from tkinter import messagebox, ttk
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from PIL import Image as PilImage
import webbrowser
import requests

class SettingsWindow:
    CONFIG_PATH = 'resources/config/settings.json'

    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func, version, downloader):
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func
        self.version = version
        self.downloader = downloader
        self.languages = {
            "Español": "es",
            "English": "en",
            "日本語": "ja",
            "中文": "zh",
            "Français": "fr",
            "Русский": "ru"
        }

        self.settings = self.load_settings()
        self.folder_structure_icons = self.load_icons()

    def load_settings(self):
        if not os.path.exists(self.CONFIG_PATH):
            return {'max_downloads': 3, 'folder_structure': 'default'}

        try:
            with open(self.CONFIG_PATH, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'max_downloads': 3, 'folder_structure': 'default'}

    def save_settings(self):
        os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
        with open(self.CONFIG_PATH, 'w') as file:
            json.dump(self.settings, file)

    def load_icons(self):
        icons = {}
        icons['folder'] = ImageTk.PhotoImage(PilImage.open("resources/img/folder.png").resize((20, 20), PilImage.Resampling.LANCZOS))
        return icons

    def open_settings(self):
        self.settings_window = ctk.CTkToplevel(self.parent)
        self.settings_window.title(self.translate("Configuraciones"))
        self.settings_window.geometry("800x700")
        self.settings_window.transient(self.parent)
        self.settings_window.grab_set()
        self.center_window(self.settings_window, 800, 700)
        self.settings_window.resizable(False, False)

        nav_frame = ctk.CTkFrame(self.settings_window, width=200)
        nav_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.content_frame = ctk.CTkFrame(self.settings_window)
        self.content_frame.pack(side="right", expand=True, fill="both", padx=(10, 20), pady=10)

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

        screen_width = self.content_frame.winfo_screenwidth()
        max_label_width = int(screen_width * 0.8)

        warning_label = ctk.CTkLabel(self.content_frame, text=self.translate("Para Coomer y Kemono, se recomienda un máximo de 3-5 descargas simultáneas para evitar errores 429."), font=("Helvetica", 12, "italic"), text_color="yellow", wraplength=max_label_width)
        warning_label.pack(pady=10)

        folder_structure_label = ctk.CTkLabel(self.content_frame, text=self.translate("Estructura de Carpetas"))
        folder_structure_label.pack(pady=10)

        self.folder_structure_combobox = ctk.CTkComboBox(self.content_frame, values=["default", "post_number"], state='readonly')
        self.folder_structure_combobox.set(self.settings.get('folder_structure', 'default'))
        self.folder_structure_combobox.pack(pady=10)

        apply_button = ctk.CTkButton(self.content_frame, text=self.translate("Aplicar"), command=self.apply_download_settings)
        apply_button.pack(pady=10)

        preview_frame = ctk.CTkFrame(self.content_frame)
        preview_frame.pack(pady=10, fill="both", expand=True)

        preview_label = ctk.CTkLabel(preview_frame, text=self.translate("Vista Previa de Estructura de Carpetas"), font=("Helvetica", 14, "bold"))
        preview_label.pack(pady=10)

        treeview_frame = ctk.CTkFrame(preview_frame)
        treeview_frame.pack(pady=10, fill="both", expand=True)

        default_tree_label = ctk.CTkLabel(treeview_frame, text=self.translate("Estructura Predeterminada"), font=("Helvetica", 12, "bold"))
        default_tree_label.grid(row=0, column=0, padx=10, pady=5)

        post_tree_label = ctk.CTkLabel(treeview_frame, text=self.translate("Estructura por Publicación"), font=("Helvetica", 12, "bold"))
        post_tree_label.grid(row=0, column=1, padx=10, pady=5)

        self.default_treeview = ttk.Treeview(treeview_frame)
        self.default_treeview.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.post_treeview = ttk.Treeview(treeview_frame)
        self.post_treeview.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        treeview_frame.grid_columnconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(1, weight=1)
        treeview_frame.grid_rowconfigure(1, weight=1)

        self.update_treeview()

    def apply_download_settings(self):
        max_downloads = int(self.max_downloads_combobox.get())
        self.settings['max_downloads'] = max_downloads
        self.settings['folder_structure'] = self.folder_structure_combobox.get()
        self.save_settings()
        self.update_treeview()  # Update the treeview when settings are applied
        self.downloader() 
        messagebox.showinfo(self.translate("Configuraciones"), self.translate("Configuraciones de descarga actualizadas"))

    def update_treeview(self):
        for item in self.default_treeview.get_children():
            self.default_treeview.delete(item)
        for item in self.post_treeview.get_children():
            self.post_treeview.delete(item)

        self.add_default_treeview_items()
        self.add_post_treeview_items()

    def add_default_treeview_items(self):
        root = self.default_treeview.insert("", "end", text="User", image=self.folder_structure_icons['folder'])
        images_node = self.default_treeview.insert(root, "end", text="images", image=self.folder_structure_icons['folder'])
        videos_node = self.default_treeview.insert(root, "end", text="videos", image=self.folder_structure_icons['folder'])
        documents_node = self.default_treeview.insert(root, "end", text="documents", image=self.folder_structure_icons['folder'])
        compressed_node = self.default_treeview.insert(root, "end", text="compressed", image=self.folder_structure_icons['folder'])
        self.default_treeview.item(root, open=True)
        self.default_treeview.item(images_node, open=True)
        self.default_treeview.item(videos_node, open=True)
        self.default_treeview.item(documents_node, open=True)
        self.default_treeview.item(compressed_node, open=True)

    def add_post_treeview_items(self):
        root = self.post_treeview.insert("", "end", text="User", image=self.folder_structure_icons['folder'])
        post = self.post_treeview.insert(root, "end", text=f"post_id", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="images", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="videos", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="documents", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="compressed", image=self.folder_structure_icons['folder'])
        post2 = self.post_treeview.insert(root, "end", text=f"post_id", image=self.folder_structure_icons['folder'])
        post3 = self.post_treeview.insert(root, "end", text=f"post_id", image=self.folder_structure_icons['folder'])
        self.post_treeview.item(root,open=True)
        self.post_treeview.item(post,open=True)

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
            latest_version = latest_release["tag_name"].lstrip('v')

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
