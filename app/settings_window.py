import json
import os
import threading
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from PIL import Image as PilImage


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
            return {'max_downloads': 3, 'folder_structure': 'default', 'language': 'en', 'theme': 'System'}

        try:
            with open(self.CONFIG_PATH, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'max_downloads': 3, 'folder_structure': 'default', 'language': 'en', 'theme': 'System'}

    def save_settings(self):
        os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
        with open(self.CONFIG_PATH, 'w') as file:
            json.dump(self.settings, file, indent=4)

    def load_icons(self):
        icons = {}
        try:
            icons['folder'] = ImageTk.PhotoImage(PilImage.open("resources/img/folder.png").resize((20, 20), PilImage.Resampling.LANCZOS))
        except Exception as e:
            messagebox.showerror(self.translate("Error"), self.translate(f"Error loading icons: {e}"))
            icons['folder'] = None
        return icons

    def open_settings(self):
        self.settings_window = ctk.CTkToplevel(self.parent)
        self.settings_window.title(self.translate("Settings"))
        self.settings_window.geometry("800x600")
        self.settings_window.transient(self.parent)
        self.settings_window.resizable(False, False)

        self.settings_window.deiconify()
        self.settings_window.after(10, self.settings_window.grab_set()) 
        self.center_window(self.settings_window, 800, 600)

        # Crear el contenedor principal con pestañas
        self.main_frame = ctk.CTkFrame(self.settings_window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Crear el CTkTabview
        self.tabview = ctk.CTkTabview(self.main_frame, width=700, height=500)
        self.tabview.pack(fill="both", expand=True)

        # Crear pestañas
        self.general_tab = self.tabview.add(self.translate("General"))
        self.downloads_tab = self.tabview.add(self.translate("Descargas"))
        self.structure_tab = self.tabview.add(self.translate("Estructura"))

        # Renderizar las pestañas
        self.render_general_tab(self.general_tab)
        self.render_downloads_tab(self.downloads_tab)
        self.render_structure_tab(self.structure_tab)

    def render_general_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)

        # Frame General
        general_frame = ctk.CTkFrame(tab, fg_color="transparent")
        general_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        general_frame.grid_columnconfigure(1, weight=1)

        # Etiqueta principal
        general_label = ctk.CTkLabel(general_frame, text=self.translate("Opciones Generales"), font=("Helvetica", 16, "bold"))
        general_label.grid(row=0, column=0, columnspan=3, sticky="w")

        # Descripción de la sección
        description_label = ctk.CTkLabel(general_frame, text=self.translate("Aquí puedes cambiar la apariencia y el idioma de la aplicación."), 
                                         font=("Helvetica", 11), text_color="gray")
        description_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # Tema
        theme_label = ctk.CTkLabel(general_frame, text=self.translate("Tema"), font=("Helvetica", 14))
        theme_label.grid(row=2, column=0, pady=5, sticky="w")

        theme_combobox = ctk.CTkComboBox(general_frame, values=["Light", "Dark", "System"], state='readonly', width=120)
        theme_combobox.set(self.settings.get('theme', 'System'))
        theme_combobox.grid(row=2, column=1, pady=5, padx=(10,0), sticky="w")

        apply_theme_button = ctk.CTkButton(general_frame, text=self.translate("Aplicar Tema"), 
                                           command=lambda: self.change_theme_in_thread(theme_combobox.get()))
        apply_theme_button.grid(row=2, column=2, pady=5, sticky="e")


        # Separador
        separator_1 = ttk.Separator(general_frame, orient="horizontal")
        separator_1.grid(row=3, column=0, columnspan=3, sticky="ew", pady=15)

        # Idioma
        language_label = ctk.CTkLabel(general_frame, text=self.translate("Idioma"), font=("Helvetica", 14))
        language_label.grid(row=4, column=0, pady=5, sticky="w")

        language_combobox = ctk.CTkComboBox(general_frame, values=list(self.languages.keys()), state='readonly', width=120)
        language_combobox.set(self.get_language_name(self.settings.get('language', 'en')))
        language_combobox.grid(row=4, column=1, pady=5, padx=(10,0), sticky="w")

        apply_language_button = ctk.CTkButton(general_frame, text=self.translate("Aplicar Idioma"),
                                              command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_language_button.grid(row=4, column=2, pady=5, sticky="e")


    def render_downloads_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Frame Descargas
        downloads_frame = ctk.CTkFrame(tab, fg_color="transparent")
        downloads_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        downloads_frame.grid_columnconfigure(1, weight=1)

        download_label = ctk.CTkLabel(downloads_frame, text=self.translate("Opciones de Descarga"), font=("Helvetica", 16, "bold"))
        download_label.grid(row=0, column=0, columnspan=3, sticky="w")

        description_label = ctk.CTkLabel(downloads_frame, text=self.translate("Aquí puedes ajustar el número de descargas simultáneas y la estructura de las carpetas."), 
                                         font=("Helvetica", 11), text_color="gray")
        description_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0,15))

        # Descargas simultáneas
        max_downloads_label = ctk.CTkLabel(downloads_frame, text=self.translate("Descargas simultáneas"))
        max_downloads_label.grid(row=2, column=0, pady=5, sticky="w")

        max_downloads_combobox = ctk.CTkComboBox(downloads_frame, values=[str(i) for i in range(1, 11)], state='readonly', width=80)
        max_downloads_combobox.set(str(self.settings.get('max_downloads', 3)))
        max_downloads_combobox.grid(row=2, column=1, pady=5, padx=(10,0), sticky="w")


        # Estructura de carpetas
        folder_structure_label = ctk.CTkLabel(downloads_frame, text=self.translate("Estructura de carpetas"))
        folder_structure_label.grid(row=3, column=0, pady=5, sticky="w")

        folder_structure_combobox = ctk.CTkComboBox(downloads_frame, values=["default", "post_number"], state='readonly', width=150)
        folder_structure_combobox.set(self.settings.get('folder_structure', 'default'))
        folder_structure_combobox.grid(row=3, column=1, pady=5, padx=(10,0), sticky="w")


        apply_download_button = ctk.CTkButton(downloads_frame, text=self.translate("Aplicar configuración de Descargas"),
                                              command=lambda: self.apply_download_settings(max_downloads_combobox, folder_structure_combobox))
        apply_download_button.grid(row=4, column=1, pady=10, sticky="e")

    def render_structure_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        structure_label = ctk.CTkLabel(tab, text=self.translate("Vista previa de la estructura de carpetas"), font=("Helvetica", 16, "bold"))
        structure_label.grid(row=0, column=0, pady=(20,10), sticky="w")

        # Descripción
        description_label = ctk.CTkLabel(tab, text=self.translate("Aquí puedes visualizar cómo se organizarán tus archivos descargados en el disco."), 
                                         font=("Helvetica", 11), text_color="gray")
        description_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0,15))

        treeview_frame = ctk.CTkFrame(tab, fg_color="transparent")
        treeview_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=20)
        treeview_frame.grid_rowconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(1, weight=1)

        self.default_treeview = ttk.Treeview(treeview_frame, show="tree")
        self.default_treeview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.post_treeview = ttk.Treeview(treeview_frame, show="tree")
        self.post_treeview.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.update_treeview()

    def apply_download_settings(self, max_downloads_combobox, folder_structure_combobox):
        try:

            max_downloads = int(max_downloads_combobox.get())
            folder_structure = folder_structure_combobox.get()

            self.settings['max_downloads'] = max_downloads
            self.settings['folder_structure'] = folder_structure


            self.save_settings()


            self.downloader.update_max_downloads(max_downloads)

            messagebox.showinfo(self.translate("Éxito"), self.translate("La configuración de descargas se ha aplicado correctamente."))
        except ValueError:
            messagebox.showerror(self.translate("Error"), self.translate("Por favor, ingresa un número válido para las descargas simultáneas."))

    def apply_language_settings(self, selected_language_name):
        if selected_language_name in self.languages:
            selected_language_code = self.languages[selected_language_name]
            self.settings['language'] = selected_language_code
            self.save_settings()
            self.save_language_preference(selected_language_code)
            self.load_translations(selected_language_code)
            self.update_ui_texts()
            messagebox.showinfo(self.translate("Éxito"), self.translate("El idioma se ha aplicado correctamente."))
        else:
            messagebox.showwarning(self.translate("Advertencia"), self.translate("Por favor, selecciona un idioma."))

    def update_treeview(self):
        """Actualiza los TreeView para mostrar la estructura de carpetas."""
        if hasattr(self, 'default_treeview') and hasattr(self, 'post_treeview'):

            self.default_treeview.delete(*self.default_treeview.get_children())
            self.post_treeview.delete(*self.post_treeview.get_children())

            root = self.default_treeview.insert("", "end", text="User", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="images", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="videos", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="documents", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="compressed", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.item(root, open=True)

            post_root = self.post_treeview.insert("", "end", text="User", image=self.folder_structure_icons.get('folder'))
            post = self.post_treeview.insert(post_root, "end", text="post_id", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="images", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="videos", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="documents", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="compressed", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.item(post_root, open=True)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def get_language_name(self, lang_code):
        for name, code in self.languages.items():
            if code == lang_code:
                return name
        return "English"

    def change_theme_in_thread(self, theme_name):
        threading.Thread(target=self.apply_theme, args=(theme_name,)).start()

    def apply_theme(self, theme_name):
        if theme_name.lower() == "light":
            ctk.set_appearance_mode("light")
        elif theme_name.lower() == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("system")
        self.settings['theme'] = theme_name
        self.save_settings()
        messagebox.showinfo(self.translate("Éxito"), self.translate("El tema se ha aplicado correctamente."))

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')
