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
        self.main_frame = ctk.CTkFrame(self.settings_window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabview = ctk.CTkTabview(self.main_frame, width=700, height=500)
        self.tabview.pack(fill="both", expand=True)
        # Existing tabs
        self.general_tab = self.tabview.add(self.translate("General"))
        self.downloads_tab = self.tabview.add(self.translate("Downloads"))
        self.structure_tab = self.tabview.add(self.translate("Structure"))
        # New tab for database
        self.db_tab = self.tabview.add(self.translate("Database"))
        self.render_general_tab(self.general_tab)
        self.render_downloads_tab(self.downloads_tab)
        self.render_structure_tab(self.structure_tab)
        self.render_db_tab(self.db_tab)
    
    def render_db_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        db_frame = ctk.CTkFrame(tab, fg_color="transparent")
        db_frame.pack(fill="both", expand=True, padx=20, pady=20)
        db_label = ctk.CTkLabel(db_frame, text=self.translate("Database Management"), font=("Helvetica", 16, "bold"))
        db_label.pack(pady=(0, 10))
        export_button = ctk.CTkButton(db_frame, text=self.translate("Export Database"), command=self.export_db)
        export_button.pack(pady=10)
        clear_button = ctk.CTkButton(db_frame, text=self.translate("Clear Database"), command=self.clear_db)
        clear_button.pack(pady=10)

    def render_general_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)

        # General frame
        general_frame = ctk.CTkFrame(tab, fg_color="transparent")
        general_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        general_frame.grid_columnconfigure(1, weight=1)

        # Main label
        general_label = ctk.CTkLabel(general_frame, text=self.translate("General Options"), font=("Helvetica", 16, "bold"))
        general_label.grid(row=0, column=0, columnspan=3, sticky="w")

        # Section description
        description_label = ctk.CTkLabel(general_frame, text=self.translate("Here you can change the appearance and language of the application."), 
                                         font=("Helvetica", 11), text_color="gray")
        description_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # Theme
        theme_label = ctk.CTkLabel(general_frame, text=self.translate("Theme"), font=("Helvetica", 14))
        theme_label.grid(row=2, column=0, pady=5, sticky="w")

        theme_combobox = ctk.CTkComboBox(general_frame, values=["Light", "Dark", "System"], state='readonly', width=120)
        theme_combobox.set(self.settings.get('theme', 'System'))
        theme_combobox.grid(row=2, column=1, pady=5, padx=(10,0), sticky="w")

        apply_theme_button = ctk.CTkButton(general_frame, text=self.translate("Apply Theme"), 
                                           command=lambda: self.change_theme_in_thread(theme_combobox.get()))
        apply_theme_button.grid(row=2, column=2, pady=5, sticky="e")

        # Separator
        separator_1 = ttk.Separator(general_frame, orient="horizontal")
        separator_1.grid(row=3, column=0, columnspan=3, sticky="ew", pady=15)

        # Language
        language_label = ctk.CTkLabel(general_frame, text=self.translate("Language"), font=("Helvetica", 14))
        language_label.grid(row=4, column=0, pady=5, sticky="w")

        language_combobox = ctk.CTkComboBox(general_frame, values=list(self.languages.keys()), state='readonly', width=120)
        language_combobox.set(self.get_language_name(self.settings.get('language', 'en')))
        language_combobox.grid(row=4, column=1, pady=5, padx=(10,0), sticky="w")

        apply_language_button = ctk.CTkButton(general_frame, text=self.translate("Apply Language"),
                                              command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_language_button.grid(row=4, column=2, pady=5, sticky="e")

    def render_downloads_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Downloads frame
        downloads_frame = ctk.CTkFrame(tab, fg_color="transparent")
        downloads_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        downloads_frame.grid_columnconfigure(1, weight=1)

        download_label = ctk.CTkLabel(downloads_frame, text=self.translate("Download Options"), font=("Helvetica", 16, "bold"))
        download_label.grid(row=0, column=0, columnspan=3, sticky="w")

        description_label = ctk.CTkLabel(downloads_frame, text=self.translate("Here you can adjust the number of simultaneous downloads and the folder structure."), 
                                         font=("Helvetica", 11), text_color="gray")
        description_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0,15))

        # Simultaneous downloads
        max_downloads_label = ctk.CTkLabel(downloads_frame, text=self.translate("Simultaneous Downloads"))
        max_downloads_label.grid(row=2, column=0, pady=5, sticky="w")

        max_downloads_combobox = ctk.CTkComboBox(downloads_frame, values=[str(i) for i in range(1, 11)], state='readonly', width=80)
        max_downloads_combobox.set(str(self.settings.get('max_downloads', 3)))
        max_downloads_combobox.grid(row=2, column=1, pady=5, padx=(10,0), sticky="w")

        # Folder structure
        folder_structure_label = ctk.CTkLabel(downloads_frame, text=self.translate("Folder Structure"))
        folder_structure_label.grid(row=3, column=0, pady=5, sticky="w")

        folder_structure_combobox = ctk.CTkComboBox(downloads_frame, values=["default", "post_number"], state='readonly', width=150)
        folder_structure_combobox.set(self.settings.get('folder_structure', 'default'))
        folder_structure_combobox.grid(row=3, column=1, pady=5, padx=(10,0), sticky="w")

        apply_download_button = ctk.CTkButton(downloads_frame, text=self.translate("Apply Download Settings"),
                                              command=lambda: self.apply_download_settings(max_downloads_combobox, folder_structure_combobox))
        apply_download_button.grid(row=4, column=1, pady=10, sticky="e")

    def render_structure_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        structure_label = ctk.CTkLabel(tab, text=self.translate("Folder Structure Preview"), font=("Helvetica", 16, "bold"))
        structure_label.grid(row=0, column=0, pady=(20,10), sticky="w")

        # Description
        description_label = ctk.CTkLabel(tab, text=self.translate("Here you can see how your downloaded files will be organized on disk."), 
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
    
    def export_db(self):
        db_path = self.downloader.db_path
        if os.path.exists(db_path):
            export_path = filedialog.asksaveasfilename(defaultextension=".db", 
                                                       filetypes=[("SQLite DB", "*.db")],
                                                       title=self.translate("Export Database"))
            if export_path:
                try:
                    import shutil
                    shutil.copy(db_path, export_path)
                    messagebox.showinfo(self.translate("Success"), self.translate("The database was exported successfully."))
                except Exception as e:
                    messagebox.showerror(self.translate("Error"), self.translate(f"Error exporting database: {e}"))
        else:
            messagebox.showwarning(self.translate("Warning"), self.translate("Database not found."))

    def clear_db(self):
        confirm = messagebox.askyesno(self.translate("Confirm"), 
                                      self.translate("Are you sure you want to clear the database? This will delete all download records."))
        if confirm:
            try:
                self.downloader.clear_database()
                messagebox.showinfo(self.translate("Success"), self.translate("The database was cleared successfully."))
            except Exception as e:
                messagebox.showerror(self.translate("Error"), self.translate(f"Error clearing database: {e}"))

    def apply_download_settings(self, max_downloads_combobox, folder_structure_combobox):
        try:
            max_downloads = int(max_downloads_combobox.get())
            folder_structure = folder_structure_combobox.get()

            self.settings['max_downloads'] = max_downloads
            self.settings['folder_structure'] = folder_structure

            self.save_settings()

            self.downloader.update_max_downloads(max_downloads)

            messagebox.showinfo(self.translate("Success"), self.translate("Download settings applied successfully."))
        except ValueError:
            messagebox.showerror(self.translate("Error"), self.translate("Please enter a valid number for simultaneous downloads."))

    def apply_language_settings(self, selected_language_name):
        if selected_language_name in self.languages:
            selected_language_code = self.languages[selected_language_name]
            self.settings['language'] = selected_language_code
            self.save_settings()
            self.save_language_preference(selected_language_code)
            self.load_translations(selected_language_code)
            self.update_ui_texts()
            messagebox.showinfo(self.translate("Success"), self.translate("The language was applied successfully."))
        else:
            messagebox.showwarning(self.translate("Warning"), self.translate("Please select a language."))

    def update_treeview(self):
        """Update the TreeViews to display the folder structure."""
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
        messagebox.showinfo(self.translate("Success"), self.translate("The theme was applied successfully."))

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')
