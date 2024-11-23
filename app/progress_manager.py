import customtkinter as ctk
import os

class ProgressManager:
    def __init__(self, progress_frame, icons, footer_speed_label, footer_eta_label, progress_details_frame, progress_bar, progress_percentage):
        self.progress_frame = progress_frame
        self.icons = icons
        self.footer_speed_label = footer_speed_label
        self.footer_eta_label = footer_eta_label
        self.progress_details_frame = progress_details_frame
        self.progress_bar = progress_bar
        self.progress_percentage = progress_percentage
        self.progress_bars = {}

    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None):
        if total > 0:
            percentage = (downloaded / total) * 100
            if file_id is None:
                self.progress_bar.set(downloaded / total)
                self.progress_percentage.configure(text=f"{percentage:.2f}%")
            else:
                if file_id not in self.progress_bars:
                    file_name = os.path.basename(file_path)
                    file_extension = os.path.splitext(file_path)[1].lower()

                    # Determinar el icono
                    if file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
                        icon = self.icons['image']
                    elif file_extension in ['.mp4', '.avi', '.mkv']:
                        icon = self.icons['video']
                    elif file_extension in ['.zip', '.rar']:
                        icon = self.icons['zip']
                    else:
                        icon = self.icons['default']

                    progress_bar_frame = ctk.CTkFrame(self.progress_details_frame)
                    progress_bar_frame.grid(row=len(self.progress_bars), column=0, sticky='ew', padx=5, pady=5)

                    # Crear un contenedor para el icono y el texto
                    icon_and_text_frame = ctk.CTkFrame(progress_bar_frame)
                    icon_and_text_frame.grid(row=0, column=0, sticky='w')

                    # Crear el icono con ctk.CTkLabel
                    icon_label = ctk.CTkLabel(icon_and_text_frame, image=icon, text="")
                    icon_label.grid(row=0, column=0, padx=5, pady=5)

                    # Limitar el texto y mostrar puntos suspensivos si excede el límite
                    max_text_length = 30
                    if len(file_name) > max_text_length:
                        displayed_file_name = file_name[:max_text_length] + '...'
                    else:
                        displayed_file_name = file_name

                    progress_label = ctk.CTkLabel(icon_and_text_frame, text=displayed_file_name, anchor='w')
                    progress_label.grid(row=0, column=1, padx=5, pady=5)

                    # Crear barra de progreso y etiquetas de porcentaje y ETA
                    progress_bar = ctk.CTkProgressBar(progress_bar_frame)
                    progress_bar.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

                    percentage_label = ctk.CTkLabel(progress_bar_frame, text=f"{percentage:.2f}%")
                    percentage_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')

                    eta_label = ctk.CTkLabel(progress_bar_frame, text=f"ETA: N/A")
                    eta_label.grid(row=2, column=1, padx=5, pady=5, sticky='e')

                    self.progress_bars[file_id] = (progress_bar, percentage_label, eta_label, progress_bar_frame)

                self.progress_bars[file_id][0].set(downloaded / total)
                self.progress_bars[file_id][1].configure(text=f"{percentage:.2f}%")
                if eta is not None:
                    eta_text = f"ETA: {int(eta // 60)}m {int(eta % 60)}s"
                    self.progress_bars[file_id][2].configure(text=eta_text)

                if downloaded >= total:
                    self.progress_frame.after(2000, lambda: self.remove_progress_bar(file_id))
        else:
            if file_id is None:
                self.progress_bar.set(0)
                self.progress_percentage.configure(text="0%")
            else:
                if file_id in self.progress_bars:
                    self.progress_bars[file_id][0].set(0)
                    self.progress_bars[file_id][1].configure(text="0%")
                    self.progress_bars[file_id][2].configure(text="ETA: N/A")

        # Actualizar velocidad en el footer (si corresponde)
        if speed is not None:
            speed_text = f"Speed: {speed / 1024:.2f} KB/s" if speed < 1048576 else f"Speed: {speed / 1048576:.2f} MB/s"
            self.footer_speed_label.configure(text=speed_text)
            self.footer_eta_label.configure(text=self.footer_eta_label.cget("text"))

    def remove_progress_bar(self, file_id):
        if file_id in self.progress_bars:
            self.progress_bars[file_id][3].grid_forget()
            del self.progress_bars[file_id]

    def update_global_progress(self, completed_files, total_files):
        if total_files > 0:
            percentage = (completed_files / total_files) * 100
            self.progress_bar.set(completed_files / total_files)
            self.progress_percentage.configure(text=f"{percentage:.2f}%")

    def toggle_progress_details(self):
        if self.progress_details_frame.winfo_ismapped():
            self.progress_details_frame.place_forget()
        else:
            self.progress_details_frame.place(relx=0.5, rely=0.5, anchor='center')
            self.progress_details_frame.lift()

    def center_progress_details_frame(self):
        self.progress_details_frame.update_idletasks()
        width = self.progress_details_frame.winfo_width()
        height = self.progress_details_frame.winfo_height()
        x = (self.progress_frame.winfo_width() // 2) - (width // 2)
        y = (self.progress_frame.winfo_height() // 2) - (height // 2)
        self.progress_details_frame.place(x=x, y=y, anchor='nw')