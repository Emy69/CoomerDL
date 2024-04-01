from tkinter import messagebox
import customtkinter as ctk
import tkinter as tk
import webbrowser
import customtkinter as ctk
from tkinter import PhotoImage, Label,Frame

def open_language_settings(app_instance):
    t = app_instance.translations[app_instance.current_language]

    language_window = ctk.CTkToplevel(app_instance)
    language_window.title(t["select_language"])
    window_width = 300
    window_height = 150
    position_right = int(app_instance.winfo_screenwidth() / 2 - window_width / 2)
    position_down = int(app_instance.winfo_screenheight() / 2 - window_height / 2)
    language_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")

    language_label = ctk.CTkLabel(language_window, text=t["select_language"])
    language_label.pack(pady=(10, 5))

    # Actualiza aquí para mapear correctamente el valor seleccionado a las claves de idioma
    language_options = {"English": "english", "Español": "spanish", "中文": "chinese"}
    selected_language_name = ctk.StringVar(value="English" if app_instance.current_language == "english" else "Español" if app_instance.current_language == "spanish" else "中文")

    language_combobox = ctk.CTkComboBox(language_window, values=list(language_options.keys()), variable=selected_language_name, state="readonly")
    language_combobox.pack(pady=5, fill='x', padx=20)

    apply_button = ctk.CTkButton(
        language_window, 
        text=t["apply"], 
        command=lambda: set_language(app_instance, language_options[selected_language_name.get()])
    )
    apply_button.pack(pady=(10, 0), fill='x', padx=20)

    language_window.transient(app_instance)
    language_window.grab_set()
    app_instance.wait_window(language_window)

def set_language(app_instance, language):
    app_instance.current_language = language
    app_instance.apply_translations()
    app_instance.save_language_preference()


def show_about_dialog(app_instance):
    current_language = app_instance.current_language  # Asegúrate de tener esta propiedad en tu instancia de aplicación
    translations = app_instance.translations[current_language]

    about_window = ctk.CTkToplevel(app_instance)
    about_window.title(translations["about_title"])
    about_window_width = 400
    about_window_height = 200
    center_x, center_y = calculate_center_position(app_instance, about_window_width, about_window_height)
    about_window.geometry(f"{about_window_width}x{about_window_height}+{center_x}+{center_y}")
    about_window.resizable(False, False)

    about_label = ctk.CTkLabel(about_window, text=translations["about_message"], wraplength=380)
    about_label.pack(expand=True)

    close_button = ctk.CTkButton(about_window, text=translations["close_button"], command=about_window.destroy)
    close_button.pack(pady=(0, 20))

    about_window.transient(app_instance)
    about_window.grab_set()
    app_instance.wait_window(about_window)

def calculate_center_position(app_instance, window_width, window_height):
    main_window_x = app_instance.winfo_x()
    main_window_y = app_instance.winfo_y()
    main_window_width = app_instance.winfo_width()
    main_window_height = app_instance.winfo_height()
    center_x = main_window_x + (main_window_width // 2) - (window_width // 2)
    center_y = main_window_y + (main_window_height // 2) - (window_height // 2)
    return center_x, center_y

def open_github():
    github_url = "https://github.com/Emy69/CoomerDL"
    webbrowser.open(github_url)
