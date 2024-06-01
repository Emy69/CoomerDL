import customtkinter as ctk

class SettingsWindow:
    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func):
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func
        self.languages = {
            "Español": "es",
            "English": "en",
            "日本語": "ja",
            "日语": "zh",
            "Français": "fr",
            "Português": "pt",
            "Русский": "ru"
        }

    def open_settings(self):
        settings_window = ctk.CTkToplevel(self.parent)
        settings_window.title(self.translate("Configuraciones"))
        settings_window.geometry("800x600")
        settings_window.transient(self.parent)
        settings_window.grab_set()

        options_frame = ctk.CTkFrame(settings_window, width=200)
        options_frame.pack(side="left", fill="y", padx=10, pady=10)

        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        language_button = ctk.CTkButton(options_frame, text=self.translate("Idioma"), command=lambda: self.show_language_settings(settings_frame))
        language_button.pack(pady=5, fill='x')

        download_button = ctk.CTkButton(options_frame, text=self.translate("ConfiguracionDescarga"), command=lambda: self.show_download_settings(settings_frame))
        download_button.pack(pady=5, fill='x')

    def show_language_settings(self, parent_frame):
        for widget in parent_frame.winfo_children():
            widget.destroy()

        language_label = ctk.CTkLabel(parent_frame, text=self.translate("Selecciona idioma"), font=("Helvetica", 16, "bold"))
        language_label.pack(pady=10)

        language_combobox = ctk.CTkComboBox(parent_frame, values=list(self.languages.keys()), state='readonly')
        language_combobox.pack(pady=10)

        apply_button = ctk.CTkButton(parent_frame, text=self.translate("Aplicar"), command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_button.pack(pady=10)

    def show_download_settings(self, parent_frame):
        for widget in parent_frame.winfo_children():
            widget.destroy()

        download_path_label = ctk.CTkLabel(parent_frame, text=self.translate("Ruta de descarga:"), font=("Helvetica", 16, "bold"))
        download_path_label.pack(pady=10)

        download_path_entry = ctk.CTkEntry(parent_frame, width=400)
        download_path_entry.pack(pady=10)

        save_path_button = ctk.CTkButton(parent_frame, text=self.translate("Guardar"), command=lambda: self.save_download_path(download_path_entry.get()))
        save_path_button.pack(pady=10)

    def apply_language_settings(self, selected_language_name):
        selected_language_code = self.languages[selected_language_name]
        self.save_language_preference(selected_language_code)