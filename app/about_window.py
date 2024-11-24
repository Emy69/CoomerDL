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
        about_window.geometry("550x550")  
        about_window.resizable(False, False)

        # Centrar la ventana
        self.center_window(about_window, 550, 550)

        # Hacer que la ventana aparezca al frente
        about_window.transient(self.parent)
        about_window.lift()
        about_window.grab_set()

        # Crear un marco para el contenido
        about_frame = ctk.CTkFrame(about_window, corner_radius=15)
        about_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew") 

        # Encabezado estilizado
        header_label = ctk.CTkLabel(
            about_frame, 
            text=self.translate("About This App"), 
            font=("Helvetica", 28, "bold"),
            text_color="white"
        )
        header_label.grid(row=0, column=0, pady=(20, 10), columnspan=3) 

        # Separador decorativo
        separator = ctk.CTkFrame(about_frame, height=2, fg_color="gray")
        separator.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="ew")  

        # Descripción con estilo
        description_text = (
            f"{self.translate('Developed by')}: Emy69\n\n"
            f"{self.translate('Version')}: {self.version}\n\n"
            f"{self.translate('This application helps users download and manage media content efficiently from various online sources.')}"
        )
        description_label = ctk.CTkLabel(
            about_frame, 
            text=description_text, 
            font=("Helvetica", 14), 
            wraplength=550, 
            justify="center",  
            text_color="white"
        )
        description_label.grid(row=2, column=0, pady=(10, 20), columnspan=3)  

        # Separador decorativo
        separator2 = ctk.CTkFrame(about_frame, height=2, fg_color="gray")
        separator2.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")  

        # Páginas soportadas
        supported_pages_label = ctk.CTkLabel(
            about_frame, 
            text=self.translate("Supported Pages"), 
            font=("Helvetica", 18, "bold"),
            text_color="white"
        )
        supported_pages_label.grid(row=4, column=0, pady=(20, 10), columnspan=3) 

       
        page_urls = [
            ("coomer.su", "https://coomer.su"),
            ("kemono.su", "https://kemono.su"),
            ("erome.com", "https://erome.com"),
            ("bunkr-albums.io", "https://bunkr-albums.io"),
            ("simpcity.su", "https://simpcity.su"),
            ("jpg5.su", "https://jpg5.su")
        ]

        row, col = 5, 0  
        for page_name, url in page_urls:
            url_button = ctk.CTkButton(
                about_frame,
                text=page_name,
                font=("Helvetica", 14),
                fg_color="transparent",
                hover_color="gray25",
                command=lambda u=url: webbrowser.open(u)
            )
            url_button.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            col += 1
            if col > 2: 
                col = 0
                row += 1

        # Botón estilizado para GitHub
        repo_button = ctk.CTkButton(
            about_frame,
            text="GitHub: Emy69/CoomerDL",
            font=("Helvetica", 14, "bold"),
            fg_color="transparent",
            hover_color="gray25",
            command=lambda: webbrowser.open("https://github.com/Emy69/CoomerDL")
        )
        repo_button.grid(row=row, column=0, columnspan=3, pady=(10, 20), sticky="n")

        # Footer con agradecimientos
        footer_label = ctk.CTkLabel(
            about_frame, 
            text=self.translate("Thank you for using our app!"), 
            font=("Helvetica", 12, "italic"), 
            text_color="white"
        )
        footer_label.grid(row=row + 1, column=0, columnspan=3, pady=(10, 20), sticky="n")  

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()