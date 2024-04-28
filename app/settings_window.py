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
        settings_window.geometry("400x300")
        settings_window.transient(self.parent)  
        settings_window.grab_set()

        options_frame = ctk.CTkFrame(settings_window, width=100)
        options_frame.pack(side="left", fill="y")

        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(side="right", expand=True, fill="both")

        language_button = ctk.CTkButton(options_frame, text=self.translate("Idioma"), command=lambda: self.show_language_settings(settings_frame))
        language_button.pack(pady=5)

    def show_language_settings(self, parent_frame):
        for widget in parent_frame.winfo_children():
            widget.destroy()

        language_label = ctk.CTkLabel(parent_frame, text=self.translate("Selecciona_idioma"))
        language_label.pack()

        language_combobox = ctk.CTkComboBox(parent_frame, values=list(self.languages.keys()), state='readonly')
        language_combobox.pack()

        apply_button = ctk.CTkButton(parent_frame, text=self.translate("Aplicar"), command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_button.pack(pady=10)

    def apply_language_settings(self, selected_language_name):
        selected_language_code = self.languages[selected_language_name]
        self.save_language_preference(selected_language_code)