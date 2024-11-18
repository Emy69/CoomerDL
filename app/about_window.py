import customtkinter as ctk
import webbrowser

class AboutWindow:
    def __init__(self, parent, translate, version):
        self.parent = parent
        self.translate = translate
        self.version = version

    def show_about(self):
        # Crear una nueva ventana
        about_window = ctk.CTkToplevel(self.parent)
        about_window.title(self.translate("About"))
        about_window.geometry("600x700")  # Ajusta el tamaño según sea necesario
        about_window.resizable(False, False)

        # Centrar la ventana
        self.center_window(about_window, 600, 300)

        # Hacer que la ventana aparezca al frente
        about_window.transient(self.parent)
        about_window.lift()
        about_window.grab_set()  # Opcional: bloquea la interacción con la ventana principal hasta que se cierre la ventana "About"

        # Crear un marco para el contenido
        about_frame = ctk.CTkFrame(about_window)
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
        description_label = ctk.CTkLabel(about_frame, text=description_text, font=("Helvetica", 14), wraplength=550, justify="left")
        description_label.pack(pady=10, padx=20)

        # Enlace al repositorio de GitHub con estilo
        repo_link = ctk.CTkButton(about_frame, text="GitHub: Emy69/CoomerDL", command=lambda: webbrowser.open("https://github.com/Emy69/CoomerDL"), hover_color="lightblue")
        repo_link.pack(pady=10)

        # Separador personalizado antes de los contribuyentes
        separator2 = ctk.CTkFrame(about_frame, height=2, fg_color="gray")
        separator2.pack(fill='x', padx=20, pady=10)

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()