# This script defines a configuration window for an application using the CustomTkinter library.
# It allows users to manage application settings such as language, download preferences, and folder structure.
# Additionally, it provides features for checking updates and displaying information about the application.

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
    CONFIG_PATH = 'resources/config/settings.json'  # Path to the configuration JSON file.

    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func, version, downloader):
        """
        Initialize the SettingsWindow class.
        
        :param parent: Parent widget (usually the main application window).
        :param translate: Function to translate text.
        :param load_translations_func: Function to load translations based on the selected language.
        :param update_ui_texts_func: Function to update UI text elements after changing the language.
        :param save_language_preference_func: Function to save the user's language preference.
        :param version: The current version of the application.
        :param downloader: Function to manage download tasks, potentially used after updating settings.
        """
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func
        self.version = version
        self.downloader = downloader
        self.languages = {  # Dictionary of available languages and their corresponding codes.
            "Español": "es",
            "English": "en",
            "日本語": "ja",
            "中文": "zh",
            "Français": "fr",
            "Русский": "ru"
        }

        self.settings = self.load_settings()  # Load settings from the JSON file, or use defaults if unavailable.
        self.folder_structure_icons = self.load_icons()  # Load icons for use in the UI.

    def load_settings(self):
        """
        Load the application settings from a JSON file.
        If the file does not exist or is corrupted, default settings are used.
        
        :return: A dictionary containing the application settings.
        """
        if not os.path.exists(self.CONFIG_PATH):
            return {'max_downloads': 3, 'folder_structure': 'default'}

        try:
            with open(self.CONFIG_PATH, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'max_downloads': 3, 'folder_structure': 'default'}

    def save_settings(self):
        """
        Save the current settings to the JSON configuration file.
        Creates the necessary directories if they do not exist.
        """
        os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
        with open(self.CONFIG_PATH, 'w') as file:
            json.dump(self.settings, file)

    def load_icons(self):
        """
        Load and resize icons from image files for use in the UI.
        
        :return: A dictionary containing the loaded icons.
        """
        icons = {}
        icons['folder'] = ImageTk.PhotoImage(PilImage.open("resources/img/folder.png").resize((20, 20), PilImage.Resampling.LANCZOS))
        return icons

    def open_settings(self):
        """
        Open the settings window and define its basic layout.
        The window includes a navigation panel on the left and a content area on the right.
        """
        self.settings_window = ctk.CTkToplevel(self.parent)
        self.settings_window.title(self.translate("Settings"))
        self.settings_window.geometry("800x700")
        self.settings_window.transient(self.parent)
        self.settings_window.grab_set()  # Makes the settings window modal (blocks interaction with the parent window).
        self.center_window(self.settings_window, 800, 700)
        self.settings_window.resizable(False, False)

        # Navigation frame for category buttons
        nav_frame = ctk.CTkFrame(self.settings_window, width=200)
        nav_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Content frame for displaying different settings categories
        self.content_frame = ctk.CTkFrame(self.settings_window)
        self.content_frame.pack(side="right", expand=True, fill="both", padx=(10, 20), pady=10)

        # Create navigation buttons for different settings categories
        self.create_nav_button(nav_frame, "Language", self.show_language_settings)
        self.create_nav_button(nav_frame, "Check for Updates", self.show_update_settings)
        self.create_nav_button(nav_frame, "Downloads", self.show_download_settings)
        self.create_nav_button(nav_frame, "About", self.show_about)

    def create_nav_button(self, parent, text, command):
        """
        Create a navigation button for the settings window.

        :param parent: The parent widget where the button will be placed.
        :param text: The text displayed on the button.
        :param command: The function to call when the button is clicked.
        """
        button = ctk.CTkButton(parent, text=self.translate(text), command=command)
        button.pack(pady=5, fill='x')

    def show_language_settings(self):
        """
        Display the language settings UI, allowing the user to select a different language.
        """
        self.clear_frame(self.content_frame)

        language_label = ctk.CTkLabel(self.content_frame, text=self.translate("Select Language"), font=("Helvetica", 16, "bold"))
        language_label.pack(pady=10)

        language_combobox = ctk.CTkComboBox(self.content_frame, values=list(self.languages.keys()), state='readonly')
        language_combobox.pack(pady=10)

        apply_button = ctk.CTkButton(self.content_frame, text=self.translate("Apply"), command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_button.pack(pady=10)

    def show_download_settings(self):
        """
        Display the download settings UI, allowing the user to configure download-related preferences.
        """
        self.clear_frame(self.content_frame)

        download_label = ctk.CTkLabel(self.content_frame, text=self.translate("Download Options"), font=("Helvetica", 16, "bold"))
        download_label.pack(pady=10)

        max_downloads_label = ctk.CTkLabel(self.content_frame, text=self.translate("Simultaneous Downloads"))
        max_downloads_label.pack(pady=10)

        # Combobox to select the maximum number of simultaneous downloads
        self.max_downloads_combobox = ctk.CTkComboBox(self.content_frame, values=[str(i) for i in range(1, 11)], state='readonly')
        self.max_downloads_combobox.set(str(self.settings.get('max_downloads', 3)))
        self.max_downloads_combobox.pack(pady=10)

        # Warning about recommended download limits for specific platforms
        screen_width = self.content_frame.winfo_screenwidth()
        max_label_width = int(screen_width * 0.8)

        warning_label = ctk.CTkLabel(self.content_frame, text=self.translate("For Coomer and Kemono, it is recommended to limit simultaneous downloads to 3-5 to avoid 429 errors."), font=("Helvetica", 12, "italic"), text_color="yellow", wraplength=max_label_width)
        warning_label.pack(pady=10)

        # Combobox to select the folder structure for downloads
        folder_structure_label = ctk.CTkLabel(self.content_frame, text=self.translate("Folder Structure"))
        folder_structure_label.pack(pady=10)

        self.folder_structure_combobox = ctk.CTkComboBox(self.content_frame, values=["default", "post_number"], state='readonly')
        self.folder_structure_combobox.set(self.settings.get('folder_structure', 'default'))
        self.folder_structure_combobox.pack(pady=10)

        # Apply button to save the download settings
        apply_button = ctk.CTkButton(self.content_frame, text=self.translate("Apply"), command=self.apply_download_settings)
        apply_button.pack(pady=10)

        # Frame to display a preview of the folder structure
        preview_frame = ctk.CTkFrame(self.content_frame)
        preview_frame.pack(pady=10, fill="both", expand=True)

        preview_label = ctk.CTkLabel(preview_frame, text=self.translate("Folder Structure Preview"), font=("Helvetica", 14, "bold"))
        preview_label.pack(pady=10)

        # TreeView frame for displaying folder structure examples
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

        # Configure the grid layout to allow the treeviews to expand
        treeview_frame.grid_columnconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(1, weight=1)
        treeview_frame.grid_rowconfigure(1, weight=1)

        # Update the treeviews with the current folder structure settings
        self.update_treeview()

    def apply_download_settings(self):
        """
        Apply the selected download settings, save them to the configuration file, and update the UI.
        This includes updating the folder structure preview and potentially triggering the downloader function.
        """
        max_downloads = int(self.max_downloads_combobox.get())
        self.settings['max_downloads'] = max_downloads  # Update the max downloads setting
        self.settings['folder_structure'] = self.folder_structure_combobox.get()  # Update the folder structure setting
        self.save_settings()  # Save the updated settings to the configuration file
        self.update_treeview()  # Refresh the folder structure preview
        self.downloader()  # Trigger the downloader function if necessary
        messagebox.showinfo(self.translate("Settings"), self.translate("Download settings updated"))

    def update_treeview(self):
        """
        Update the TreeViews that display the folder structure previews.
        The TreeViews are cleared and repopulated based on the current settings.
        """
        # Clear existing items in the TreeViews
        for item in self.default_treeview.get_children():
            self.default_treeview.delete(item)
        for item in self.post_treeview.get_children():
            self.post_treeview.delete(item)

        # Add items to the TreeViews based on the selected folder structure
        self.add_default_treeview_items()
        self.add_post_treeview_items()

    def add_default_treeview_items(self):
        """
        Populate the default structure TreeView with a sample folder hierarchy.
        This represents how files would be organized using the 'default' folder structure setting.
        """
        root = self.default_treeview.insert("", "end", text="User", image=self.folder_structure_icons['folder'])
        images_node = self.default_treeview.insert(root, "end", text="images", image=self.folder_structure_icons['folder'])
        videos_node = self.default_treeview.insert(root, "end", text="videos", image=self.folder_structure_icons['folder'])
        documents_node = self.default_treeview.insert(root, "end", text="documents", image=self.folder_structure_icons['folder'])
        compressed_node = self.default_treeview.insert(root, "end", text="compressed", image=self.folder_structure_icons['folder'])

        # Automatically expand the nodes to show the folder structure
        self.default_treeview.item(root, open=True)
        self.default_treeview.item(images_node, open=True)
        self.default_treeview.item(videos_node, open=True)
        self.default_treeview.item(documents_node, open=True)
        self.default_treeview.item(compressed_node, open=True)

    def add_post_treeview_items(self):
        """
        Populate the post-based structure TreeView with a sample folder hierarchy.
        This represents how files would be organized using the 'post_number' folder structure setting.
        """
        root = self.post_treeview.insert("", "end", text="User", image=self.folder_structure_icons['folder'])
        post = self.post_treeview.insert(root, "end", text=f"post_id", image=self.folder_structure_icons['folder'])
        
        # Add subfolders under the post folder
        self.post_treeview.insert(post, "end", text="images", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="videos", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="documents", image=self.folder_structure_icons['folder'])
        self.post_treeview.insert(post, "end", text="compressed", image=self.folder_structure_icons['folder'])

        # Optionally, add more post folders as examples
        post2 = self.post_treeview.insert(root, "end", text=f"post_id", image=self.folder_structure_icons['folder'])
        post3 = self.post_treeview.insert(root, "end", text=f"post_id", image=self.folder_structure_icons['folder'])

        # Automatically expand the nodes to show the folder structure
        self.post_treeview.item(root, open=True)
        self.post_treeview.item(post, open=True)

    def show_general_settings(self):
        """
        Display general settings that are not specific to any particular category.
        This can include options that affect the overall behavior of the application.
        """
        self.clear_frame(self.content_frame)

        general_label = ctk.CTkLabel(self.content_frame, text=self.translate("General Options"), font=("Helvetica", 16, "bold"))
        general_label.pack(pady=10)

    def show_update_settings(self):
        """
        Display the update settings UI, allowing the user to manually check for application updates.
        """
        self.clear_frame(self.content_frame)

        update_label = ctk.CTkLabel(self.content_frame, text=self.translate("Check for Updates"), font=("Helvetica", 16, "bold"))
        update_label.pack(pady=10)

        update_button = ctk.CTkButton(self.content_frame, text=self.translate("Check"), command=self.check_for_updates)
        update_button.pack(pady=10)

    def show_about(self):
        """
        Display the 'About' section, which provides information about the application,
        such as the developer's name, version number, and links to the repository or website.
        """
        self.clear_frame(self.content_frame)

        about_label = ctk.CTkLabel(self.content_frame, text=self.translate("About"), font=("Helvetica", 20, "bold"))
        about_label.pack(pady=20)

        description_text = f"""
        {self.translate("Developed by: Emy69")}

        {self.translate("Version")}: {self.version}

        {self.translate("Repository")}: 
        """
        description_label = ctk.CTkLabel(self.content_frame, text=description_text, font=("Helvetica", 14))
        description_label.pack(pady=10)

        repo_link = ctk.CTkButton(self.content_frame, text="GitHub: Emy69/CoomerDL", command=lambda: webbrowser.open("https://github.com/Emy69/CoomerDL"))
        repo_link.pack(pady=10)

        contributors_label = ctk.CTkLabel(self.content_frame, text=self.translate("Contributors"), font=("Helvetica", 16, "bold"))
        contributors_label.pack(pady=20)

        self.show_contributors()

    def apply_language_settings(self, selected_language_name):
        """
        Apply the selected language, save the preference, and update the UI texts.
        
        :param selected_language_name: The name of the language selected by the user.
        """
        selected_language_code = self.languages[selected_language_name]
        self.save_language_preference(selected_language_code)
        self.load_translations(selected_language_code)
        self.update_ui_texts()

    def clear_frame(self, frame):
        """
        Clear all widgets from a given frame, effectively resetting the UI area.
        
        :param frame: The frame to be cleared.
        """
        for widget in frame.winfo_children():
            widget.destroy()

    def create_photoimage(self, path, size=(32, 32)):
        """
        Create a PhotoImage from a given file path, resized to the specified dimensions.
        
        :param path: Path to the image file.
        :param size: Tuple specifying the desired size (width, height).
        :return: A PhotoImage object for use in the UI.
        """
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)
        photoimg = ImageTk.PhotoImage(img)
        return photoimg

    def update_all_widgets(self, widget):
        """
        Recursively update all widgets in a given widget tree to ensure they reflect the latest UI state.
        
        :param widget: The root widget whose children will be updated.
        """
        for child in widget.winfo_children():
            if isinstance(child, (ctk.CTkFrame, ctk.CTkButton, ctk.CTkLabel, ctk.CTkComboBox)):
                child.update()
            self.update_all_widgets(child)

    def center_window(self, window, width, height):
        """
        Center a window on the screen based on its width and height.
        
        :param window: The window to be centered.
        :param width: The width of the window.
        :param height: The height of the window.
        """
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def check_for_updates(self):
        """
        Check for the latest version of the application using the GitHub API.
        If a new version is available, prompt the user to download it.
        """
        api_url = "https://api.github.com/repos/Emy69/CoomerDL/releases/latest"

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release["tag_name"].lstrip('v')

            if latest_version != self.version.lstrip('v'):
                if messagebox.askyesno(self.translate("Update Available"),
                                       self.translate(f"A new version is available: {latest_version}\n"
                                                      "Would you like to go to the download page?")):
                    webbrowser.open("https://github.com/Emy69/CoomerDL/releases")
            else:
                messagebox.showinfo(self.translate("Update"),
                                    self.translate("Your software is up to date."))
        except requests.RequestException as e:
            messagebox.showerror(self.translate("Error"),
                                 self.translate(f"Unable to check for updates.\nError: {e}"))

    def show_contributors(self):
        """
        Display a list of contributors to the project by fetching data from the GitHub API.
        Each contributor's avatar, username, and profile link are displayed.
        """
        try:
            response = requests.get("https://api.github.com/repos/Emy69/CoomerDL/contributors")
            response.raise_for_status()
            contributors = response.json()

            for contributor in contributors:
                frame = ctk.CTkFrame(self.content_frame)
                frame.pack(fill='x', padx=20, pady=10)

                # Load the contributor's avatar image
                avatar_url = contributor["avatar_url"]
                avatar_image = Image.open(requests.get(avatar_url, stream=True).raw)
                avatar_image = avatar_image.resize((50, 50), Image.Resampling.LANCZOS)
                avatar_photo = ImageTk.PhotoImage(avatar_image)

                # Display the avatar image
                avatar_label = tk.Label(frame, image=avatar_photo)
                avatar_label.image = avatar_photo  # Keep a reference to avoid garbage collection
                avatar_label.pack(side="left", padx=10)

                # Display the contributor's username
                name_label = ctk.CTkLabel(frame, text=contributor["login"], font=("Helvetica", 14))
                name_label.pack(side="left", padx=10)

                # Button to open the contributor's GitHub profile
                link_button = ctk.CTkButton(frame, text=self.translate("Profile"), command=lambda url=contributor["html_url"]: webbrowser.open(url))
                link_button.pack(side="left", padx=10)

        except requests.RequestException as e:
            messagebox.showerror(self.translate("Error"), self.translate(f"Failed to load contributors.\nError: {e}"))
