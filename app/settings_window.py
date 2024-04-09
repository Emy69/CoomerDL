import json
import customtkinter as ctk
from tkinter import messagebox, ttk

class SettingsWindow:
    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func):
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func

    def open_settings(self):
        # Crea una ventana de configuraciones directamente con la ventana principal como padre
        settings_window = ctk.CTkToplevel(self.parent)  # Aquí se pasa self.parent en lugar de self
        settings_window.title(self.translate("Configuraciones"))
        settings_window.geometry("400x300")
        settings_window.transient(self.parent)  # Asegúrate de que el argumento aquí sea la ventana principal
        settings_window.grab_set()

        # Panel izquierdo para opciones de configuración
        options_frame = ctk.CTkFrame(settings_window, width=100)
        options_frame.pack(side="left", fill="y")
        
        # Panel derecho para mostrar configuraciones específicas
        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(side="right", expand=True, fill="both")
        
        # Ejemplo de opciones de configuración
        language_button = ctk.CTkButton(options_frame, text="Idioma", command=lambda: self.show_language_settings(settings_frame))
        language_button.pack(pady=5)

    def show_language_settings(self, parent_frame):
        # Limpia el marco de configuraciones existente
        for widget in parent_frame.winfo_children():
            widget.destroy()

        language_label = ctk.CTkLabel(parent_frame, text=self.translate("Selecciona un idioma:"))
        language_label.pack()

        # Actualiza el diccionario para incluir los nuevos idiomas y sus códigos
        languages = {
            "Español": "es",
            "Inglés": "en",
            "Japonés": "ja",
            "Chino": "zh",
            "Francés": "fr",
            "Portugués": "pt",
            "Ruso": "ru"
        }
        language_combobox = ctk.CTkComboBox(parent_frame, values=list(languages.keys()))
        language_combobox.pack()

        apply_button = ctk.CTkButton(parent_frame, text=self.translate("Aplicar"), command=lambda: self.apply_language_settings(language_combobox.get(), languages))
        apply_button.pack(pady=10)

    def apply_language_settings(self, selected_language_name, languages):
        selected_language_code = languages[selected_language_name]
        # Usa la referencia pasada para guardar la preferencia de idioma
        self.save_language_preference(selected_language_code)