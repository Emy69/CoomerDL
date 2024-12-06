import json
import os
import shutil
import sys
import threading
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from PIL import Image as PilImage
import webbrowser
import requests
import patoolib

class SettingsWindow:
    CONFIG_PATH = 'resources/config/settings.json'  # Path to the configuration JSON file.

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
        # Crear la ventana de configuración antes de llamar a deiconify y grab_set
        self.settings_window = ctk.CTkToplevel(self.parent)
        self.settings_window.title(self.translate("Settings"))
        self.settings_window.geometry("850x850")
        self.settings_window.transient(self.parent)
        self.settings_window.resizable(False, False)

        # Mostrar la ventana y asegurarse de que se haga visible antes de aplicar el grab
        self.settings_window.deiconify()
        self.settings_window.after(10, self.settings_window.grab_set)  # Cambio: ahora usamos self.settings_window.after
        self.center_window(self.settings_window, 850, 850)

        self.content_frame = ctk.CTkFrame(self.settings_window)
        self.content_frame.pack(side="right", expand=True, fill="both", padx=(10, 20), pady=10)


        # Mostrar la pestaña de General por defecto
        self.show_general_settings()

    def create_nav_button(self, parent, text, command):
        button = ctk.CTkButton(parent, text=self.translate(text), command=command)
        button.pack(pady=5, fill='x')

    def show_general_settings(self):
        self.clear_frame(self.content_frame)

        general_label = ctk.CTkLabel(self.content_frame, text=self.translate("General Options"), font=("Helvetica", 16, "bold"))
        general_label.grid(row=0, column=0, pady=10, sticky="w")

        # Línea divisoria
        separator_1 = ttk.Separator(self.content_frame, orient="horizontal")
        separator_1.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)

        # Configuración del tema
        theme_label = ctk.CTkLabel(self.content_frame, text=self.translate("Select Theme"), font=("Helvetica", 14))
        theme_label.grid(row=2, column=0, pady=5, sticky="w")

        theme_combobox = ctk.CTkComboBox(self.content_frame, values=["Light", "Dark", "System"], state='readonly')
        theme_combobox.grid(row=2, column=1, pady=5, padx=10, sticky="w")

        apply_theme_button = ctk.CTkButton(self.content_frame, text=self.translate("Apply Theme"), command=lambda: self.change_theme_in_thread(theme_combobox.get()))
        apply_theme_button.grid(row=2, column=2, pady=5, sticky="w")

        # Línea divisoria
        separator_2 = ttk.Separator(self.content_frame, orient="horizontal")
        separator_2.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)

        # Configuración de idioma
        language_label = ctk.CTkLabel(self.content_frame, text=self.translate("Select Language"), font=("Helvetica", 14))
        language_label.grid(row=4, column=0, pady=5, sticky="w")

        language_combobox = ctk.CTkComboBox(self.content_frame, values=list(self.languages.keys()), state='readonly')
        language_combobox.grid(row=4, column=1, pady=5, padx=10, sticky="w")

        apply_language_button = ctk.CTkButton(self.content_frame, text=self.translate("Apply Language"), command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_language_button.grid(row=4, column=2, pady=5, sticky="w")

        # Línea divisoria
        separator_3 = ttk.Separator(self.content_frame, orient="horizontal")
        separator_3.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)

        # Configuración de las opciones de descarga
        download_label = ctk.CTkLabel(self.content_frame, text=self.translate("Download Options"), font=("Helvetica", 16, "bold"))
        download_label.grid(row=6, column=0, pady=10, sticky="w")

        max_downloads_label = ctk.CTkLabel(self.content_frame, text=self.translate("Simultaneous Downloads"))
        max_downloads_label.grid(row=7, column=0, pady=5, sticky="w")

        self.max_downloads_combobox = ctk.CTkComboBox(self.content_frame, values=[str(i) for i in range(1, 11)], state='readonly')
        self.max_downloads_combobox.set(str(self.settings.get('max_downloads', 3)))
        self.max_downloads_combobox.grid(row=7, column=1, pady=5, padx=10, sticky="w")

        folder_structure_label = ctk.CTkLabel(self.content_frame, text=self.translate("Folder Structure"))
        folder_structure_label.grid(row=8, column=0, pady=5, sticky="w")

        self.folder_structure_combobox = ctk.CTkComboBox(self.content_frame, values=["default", "post_number"], state='readonly')
        self.folder_structure_combobox.set(self.settings.get('folder_structure', 'default'))
        self.folder_structure_combobox.grid(row=8, column=1, pady=5, padx=10, sticky="w")

        apply_download_button = ctk.CTkButton(self.content_frame, text=self.translate("Apply Download Settings"), command=self.apply_download_settings)
        apply_download_button.grid(row=9, column=1, pady=10, sticky="w", padx=(0, 10))

        # Línea divisoria
        separator_5 = ttk.Separator(self.content_frame, orient="horizontal")
        separator_5.grid(row=12, column=0, columnspan=3, sticky="ew", pady=5)

        # Vista previa de la estructura de carpetas con scrollbar
        treeview_label = ctk.CTkLabel(self.content_frame, text=self.translate("Folder Structure Preview"), font=("Helvetica", 14, "bold"))
        treeview_label.grid(row=13, column=0, pady=10, sticky="w")

        treeview_frame = ctk.CTkFrame(self.content_frame)
        treeview_frame.grid(row=14, column=0, columnspan=3, pady=5, sticky="nsew")

        self.default_treeview = ttk.Treeview(treeview_frame)
        self.default_treeview.pack(side="left", fill="both", expand=True)

        self.post_treeview = ttk.Treeview(treeview_frame)
        self.post_treeview.pack(side="left", fill="both", expand=True)

        self.update_treeview()


    def save_settings(self):
        with open('resources/config/settings.json', 'w') as f:
            json.dump(self.settings, f)


    def change_theme_in_thread(self, selected_theme):
        threading.Thread(target=self.apply_theme, args=(selected_theme,)).start()

    def apply_theme(self, selected_theme):
        if selected_theme == "Light":
            ctk.set_appearance_mode("light")
        elif selected_theme == "Dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("system")

    def apply_language_settings(self, selected_language_name):
        if selected_language_name in self.languages:
            selected_language_code = self.languages[selected_language_name]
            self.save_language_preference(selected_language_code)
            self.load_translations(selected_language_code)
            self.update_ui_texts()
        else:
            messagebox.showwarning(self.translate("Warning"), self.translate("Please select a language."))

    def apply_download_settings(self):
        max_downloads = int(self.max_downloads_combobox.get())
        self.settings['max_downloads'] = max_downloads
        self.settings['folder_structure'] = self.folder_structure_combobox.get()
        self.save_settings()
        self.update_treeview()

        # Actualizar la configuración del descargador
        self.parent.update_max_downloads(max_downloads)
        messagebox.showinfo(self.translate("Settings"), self.translate("Download settings updated"))

    def update_treeview(self):
        # Clear existing items in the TreeViews
        for item in self.default_treeview.get_children():
            self.default_treeview.delete(item)
        for item in self.post_treeview.get_children():
            self.post_treeview.delete(item)

        # Add header labels to distinguish the treeviews
        self.default_treeview.heading("#0", text="Default Folder Structure")
        self.post_treeview.heading("#0", text="Post-based Folder Structure")

        # Add items to the TreeViews based on the selected folder structure
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

        self.post_treeview.item(root, open=True)
        self.post_treeview.item(post, open=True)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')
