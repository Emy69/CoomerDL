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
    language_options = {"English": "english", "Español": "spanish"}
    selected_language_name = ctk.StringVar(value="English" if app_instance.current_language == "english" else "Español")
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
    about_window = ctk.CTkToplevel(app_instance)
    about_window.title("Acerca de")
    about_window_width = 500  # Ancho ampliado para un mejor layout horizontal
    about_window_height = 300  # Altura ajustada
    center_x, center_y = calculate_center_position(app_instance, about_window_width, about_window_height)
    about_window.geometry(f"{about_window_width}x{about_window_height}+{center_x}+{center_y}")
    about_window.resizable(False, False)

    # Añade la imagen del autor en el lado izquierdo
    author_image = PhotoImage(file="resources/img/icono.png")  # Asegúrate de tener esta imagen
    author_image_label = Label(about_window, image=author_image)
    author_image_label.image = author_image
    author_image_label.place(x=20, y=20)

    # Detalles de la aplicación en el lado derecho
    details_frame = ctk.CTkFrame(about_window)
    details_frame.place(x=180, y=20)

    about_message = "Coomer Downloader [Beta-V0.3]"
    about_label = ctk.CTkLabel(details_frame, text=about_message)
    about_label.pack(pady=(10, 5))

    about_detail = "Una aplicación para descargar imágenes y vídeos de manera eficiente."
    about_detail_label = ctk.CTkLabel(details_frame, text=about_detail, wraplength=280)
    about_detail_label.pack(pady=(0, 5))

    author_name = "Emy69"
    author_label = ctk.CTkLabel(details_frame, text=f"Autor: {author_name}")
    author_label.pack(pady=(0, 5))

    compatible_urls_message = "Compatible con:\nhttps://www.erome.com/\nhttps://coomer.su/\nhttps://kemono.su/"
    compatible_urls_label = ctk.CTkLabel(details_frame, text=compatible_urls_message, wraplength=280)
    compatible_urls_label.pack(pady=(0, 10))

    github_button = ctk.CTkButton(details_frame, text="GitHub", command=lambda: open_github())
    github_button.pack(pady=(0, 5))

    close_button = ctk.CTkButton(details_frame, text="Cerrar", command=about_window.destroy)
    close_button.pack(pady=(5, 10))

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
