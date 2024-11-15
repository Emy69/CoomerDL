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

        # Crear el marco de navegación y contenido
        nav_frame = ctk.CTkFrame(self.settings_window, width=200)
        nav_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.content_frame = ctk.CTkFrame(self.settings_window)
        self.content_frame.pack(side="right", expand=True, fill="both", padx=(10, 20), pady=10)

        # Crear botones de navegación
        self.create_nav_button(nav_frame, "General", self.show_general_settings)
        self.create_nav_button(nav_frame, "About", self.show_about)

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

        # Botón para seleccionar la carpeta del perfil de Chrome
        chrome_profile_button = ctk.CTkButton(self.content_frame, text=self.translate("Select Chrome Profile Folder"), command=self.select_chrome_profile_folder)
        chrome_profile_button.grid(row=15, column=0, pady=10, sticky="w", padx=(0, 10))

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
        separator_4 = ttk.Separator(self.content_frame, orient="horizontal")
        separator_4.grid(row=10, column=0, columnspan=3, sticky="ew", pady=5)

        # Chequeo de actualizaciones
        update_label = ctk.CTkLabel(self.content_frame, text=self.translate("Check for Updates"), font=("Helvetica", 16, "bold"))
        update_label.grid(row=11, column=0, pady=10, sticky="w")

        update_button = ctk.CTkButton(self.content_frame, text=self.translate("Check"), command=self.check_for_updates)
        update_button.grid(row=11, column=1, pady=10, padx=(0, 10), sticky="w")

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


    def show_update_settings(self):
        self.clear_frame(self.content_frame)

        update_label = ctk.CTkLabel(self.content_frame, text=self.translate("Check for Updates"), font=("Helvetica", 16, "bold"))
        update_label.pack(pady=10)

        update_button = ctk.CTkButton(self.content_frame, text=self.translate("Check"), command=self.check_for_updates)
        update_button.pack(pady=10)

    def show_about(self):
        self.clear_frame(self.content_frame)

        # Crear un marco para el contenido
        about_frame = ctk.CTkFrame(self.content_frame)
        about_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Título de la sección con estilo
        about_label = ctk.CTkLabel(about_frame, text=self.translate("About"), font=("Helvetica", 24, "bold"))
        about_label.pack(pady=(10, 5))

        # Separador personalizado
        separator = ctk.CTkFrame(about_frame, height=2, fg_color="gray")
        separator.pack(fill='x', padx=20, pady=10)

        # Descripción del software con estilo
        description_text = f"""
    {self.translate("Developed by")}: Emy69

    {self.translate("Version")}: {self.version}

    {self.translate("This application is designed to help users download and manage media content efficiently from various online sources.")}
        """
        description_label = ctk.CTkLabel(about_frame, text=description_text, font=("Helvetica", 14), wraplength=600, justify="left")
        description_label.pack(pady=10, padx=20)

        # Enlace al repositorio de GitHub con estilo
        repo_link = ctk.CTkButton(about_frame, text="GitHub: Emy69/CoomerDL", command=lambda: webbrowser.open("https://github.com/Emy69/CoomerDL"), hover_color="lightblue")
        repo_link.pack(pady=10)

        # Separador personalizado antes de los contribuyentes
        separator2 = ctk.CTkFrame(about_frame, height=2, fg_color="gray")
        separator2.pack(fill='x', padx=20, pady=10)

        # Sección de contribuyentes con estilo
        contributors_label = ctk.CTkLabel(about_frame, text=self.translate("Contributors"), font=("Helvetica", 18, "bold"))
        contributors_label.pack(pady=(10, 5))

        self.show_contributors(about_frame)

        # Espacio final
        final_space = ctk.CTkLabel(about_frame, text="", font=("Helvetica", 14))
        final_space.pack(pady=10)



    def show_contributors(self, parent_frame):
        try:
            response = requests.get("https://api.github.com/repos/Emy69/CoomerDL/contributors")
            response.raise_for_status()
            contributors = response.json()

            for contributor in contributors:
                frame = ctk.CTkFrame(parent_frame)
                frame.pack(fill='x', padx=20, pady=10)

                avatar_url = contributor["avatar_url"]
                avatar_image = Image.open(requests.get(avatar_url, stream=True).raw)
                avatar_image = avatar_image.resize((50, 50), PilImage.Resampling.LANCZOS)
                avatar_photo = ImageTk.PhotoImage(avatar_image)

                avatar_label = tk.Label(frame, image=avatar_photo)
                avatar_label.image = avatar_photo  # Guardar referencia para evitar recolección de basura
                avatar_label.pack(side="left", padx=10)

                name_label = ctk.CTkLabel(frame, text=contributor["login"], font=("Helvetica", 14))
                name_label.pack(side="left", padx=10)

                link_button = ctk.CTkButton(
                    frame,
                    text=self.translate("Profile"),
                    command=lambda url=contributor["html_url"]: webbrowser.open(url)
                )
                link_button.pack(side="left", padx=10)

        except requests.RequestException as e:
            messagebox.showerror(
                self.translate("Error"),
                self.translate(f"Failed to load contributors.\nError: {e}")
            )

    def check_for_updates(self):
        api_url = "https://api.github.com/repos/Emy69/CoomerDL/releases/latest"  

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release["tag_name"].lstrip('v')

            if latest_version != self.version.lstrip('v'):
                # Buscar el URL de descarga
                download_url = None
                for asset in latest_release['assets']:
                    if asset['name'].endswith(('.zip', '.rar')): 
                        download_url = asset['browser_download_url']
                        break

                if download_url:
                    if messagebox.askyesno("Update Available", f"A new version {latest_version} is available.\nWould you like to download and install it?"):
                        if self.download_and_replace(download_url):
                            messagebox.showinfo("Update", "The application has been updated. Please restart the application.")
                            sys.exit(0)  
                else:
                    messagebox.showerror("Update Error", "No downloadable asset found.")
            else:
                messagebox.showinfo("Update", "Your software is up to date.")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Unable to check for updates.\nError: {e}")

    def download_and_replace(self, url):
        # Crear una nueva ventana para mostrar el progreso
        progress_window = tk.Toplevel(self.parent)
        progress_window.title(self.translate("Progress"))
        progress_window.geometry("300x100")
        progress_window.transient(self.parent)  
        progress_window.grab_set()  

        # Centrar la ventana de progreso
        self.center_window(progress_window, 300, 100)
        
        # Barra de progreso para la descarga
        download_progress = ttk.Progressbar(progress_window, orient='horizontal', length=280, mode='determinate')
        download_progress.pack(pady=10)
        
        # Etiqueta para mostrar el estado actual
        status_label = tk.Label(progress_window, text=self.translate("Downloading..."))
        status_label.pack(pady=5)
        
        # Extraer el nombre del archivo de la URL
        file_name = url.split('/')[-1]
        
        # Preguntar al usuario dónde guardar el archivo descargado
        filetypes = [('ZIP files', '*.zip'), ('RAR files', '*.rar')]
        save_path = filedialog.asksaveasfilename(title="Save As", initialfile=file_name, defaultextension=".zip", filetypes=filetypes)
        if not save_path:
            messagebox.showinfo("Cancelled", "Download cancelled by user.")
            progress_window.destroy()
            return False
        
        # Descargar el archivo 
        response = requests.get(url, stream=True)
        total_length = int(response.headers.get('content-length', 0))
        with open(save_path, "wb") as file:
            for data in response.iter_content(chunk_size=4096):
                file.write(data)
                download_progress['value'] += len(data) / total_length * 100
                progress_window.update_idletasks()
        
        # Actualizar el estado para la descompresión
        status_label.config(text=self.translate("Extracting..."))
        progress_window.update_idletasks()
        
        # Preguntar al usuario dónde descomprimir el archivo
        target_directory = filedialog.askdirectory(title="Select Directory to Extract Files")
        if not target_directory:
            messagebox.showinfo("Cancelled", "Extraction cancelled by user.")
            progress_window.destroy()
            return False
        
        # Usar patoolib para descomprimir el archivo
        try:
            patoolib.extract_archive(save_path, outdir=target_directory)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract files.\nError: {e}")
            progress_window.destroy()
            return False
        
        # Limpiar archivo de actualización
        os.remove(save_path)
        messagebox.showinfo("Success", "Files extracted successfully.")
        progress_window.destroy()
        return True

    def select_chrome_profile_folder(self):
        folder_path = filedialog.askdirectory(title=self.translate("Select Chrome Profile Folder"))
        if folder_path:
            self.settings['chrome_profile_folder'] = folder_path
            self.save_settings()
            messagebox.showinfo(self.translate("Success"), self.translate("Chrome profile folder saved successfully."))

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
