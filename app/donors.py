import os
import customtkinter as ctk
import requests
import threading
import json
import tkinter as tk
from PIL import Image

class DonorsModal(ctk.CTkToplevel):
    def __init__(self, parent, tr):
        super().__init__(parent)
        self.parent = parent
        self.tr = tr # Translation function
        
        self.title(self.tr("Patreons"))
        self.geometry("600x600")
        self.resizable(False, False)
        self.transient(parent)

        # Centrar la ventana y crear la UI
        self.center_window()
        self.create_ui()
        self.after_idle(self._safe_grab)
        # Start loading data in a separate thread to prevent UI freeze
        threading.Thread(target=self._load_donors, daemon=True).start()
        
    def _safe_grab(self):
        """Intenta grab_set hasta que la ventana sea visible."""
        try:
            self.grab_set()
        except tk.TclError:
            # Aún no es “viewable”; reintenta en 20 ms
            self.after(20, self._safe_grab)

    def center_window(self):
        """Centers the modal window relative to the parent window."""
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        
        window_w = self.winfo_width()
        window_h = self.winfo_height()
        
        cx = parent_x + (parent_w // 2) - (window_w // 2)
        cy = parent_y + (parent_h // 2) - (window_h // 2)
        self.geometry(f"{window_w}x{window_h}+{cx}+{cy}")

    def create_ui(self):
        """Creates the UI elements for the Top Donors modal."""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            main_frame,
            text=self.tr("Patreons"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        self.donors_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        self.donors_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.grid_container = ctk.CTkFrame(self.donors_frame, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True)

        self.status_label = ctk.CTkLabel(
            self.grid_container,
            text=self.tr("Loading Patreons..."),
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.status_label.grid(pady=20)

        close_button = ctk.CTkButton(
            main_frame,
            text=self.tr("Close"),
            command=self.destroy
        )
        close_button.pack(pady=(10, 0))

    def _load_donors(self):
        """Fetches donor data from the API."""
        donors = []
        error_message = ""
        try:
            # Explicitly set Accept and User-Agent headers
            resp = requests.get(
                'https://emydevs.com/coomer/donadores.php',
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
                },
                timeout=10
            )
            resp.raise_for_status()
            donors = resp.json()
        except requests.exceptions.RequestException as req_e:
            error_message = str(req_e)
            print(f"Error fetching donors: {error_message}")
            self.after(0, lambda msg=error_message: self.status_label.configure(text=self.tr("Error fetching donors: {error}").format(error=msg), text_color="red"))
            return
        except json.JSONDecodeError as json_e:
            error_message = str(json_e)
            print(f"Error decoding JSON: {error_message}")
            self.after(0, lambda msg=error_message: self.status_label.configure(text=self.tr("Error processing donor data: {error}").format(error=msg), text_color="red"))
            return

        # Update the UI on the main thread
        self.after(0, lambda: self._show_donors(donors))

    def _show_donors(self, donors):
        """Displays donor data in the modal."""
        # Clear status label
        self.status_label.grid_forget()

        # Clear existing data
        for widget in self.grid_container.winfo_children():
            if widget is self.status_label:
                continue
            widget.destroy()
            
        columns = 2
        for c in range(columns):
            self.grid_container.grid_columnconfigure(c, weight=1)
        
        if not donors:
            empty = ctk.CTkLabel(self.grid_container, text=self.tr("No donors found."), text_color="gray")
            empty.grid(row=0, column=0, columnspan=columns, pady=20)
            return

        # Sort by amount in descending order, ensuring numeric comparison
        def _to_float(v):
            try:
                return float(v)
            except Exception:
                return 0.0
        donors.sort(key=lambda x: _to_float(x.get("donated_amount", 0)), reverse=True)

        # Cache icons once (PNG medals and default)
        if not hasattr(self, "_donor_icons"):
            icon_dir = os.path.join("resources", "img", "iconos", "donors")

            def _load_icon(fname):
                path = os.path.join(icon_dir, fname)
                if os.path.exists(path):
                    return ctk.CTkImage(
                        light_image=Image.open(path),
                        dark_image=Image.open(path),
                        size=(20, 20)
                    )
                return None

            # Keep a dict for quick access and to hold references
            self._donor_icons = {
                "gold": _load_icon("gold.png"),
                "silver": _load_icon("silver.png"),
                "bronze": _load_icon("bronze.png"),
                "default": _load_icon("default.png"),
            }
        
        # Info note about donors data update
        info_label = ctk.CTkLabel(
            self.grid_container,
            text=self.tr(
                "Note: Donor information is updated every 10th of each month.\n"
                "Names and donation amounts are retrieved from my Patreon page."
            ),
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
            justify="center",
            wraplength=350  # wrap text to fit in ~350px width
        )
        info_label.grid(row=0, column=0, columnspan=columns, pady=(0, 10), sticky="ew")

        for i, donor in enumerate(donors):
            donor_name = donor.get("name", self.tr("Unknown Donor"))

            # Select icon and colors
            icon_key = "default"
            font_size = 14
            font_weight = "normal"
            name_color = "#E0E0E0"

            icon_img = self._donor_icons.get(icon_key)

            # Row container
            donor_row_frame = ctk.CTkFrame(self.grid_container, fg_color="transparent", corner_radius=8)
            donor_row_frame.grid_columnconfigure(0, weight=0)
            donor_row_frame.grid_columnconfigure(1, weight=1)
            row = (i // columns) + 1
            col = i % columns
            donor_row_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            # Rank label with icon
            rank_label = ctk.CTkLabel(
                donor_row_frame,
                text="", # remove numeric order
                image=icon_img,
                compound="left",
                font=ctk.CTkFont(size=font_size, weight=font_weight),
                width=40,
                anchor="w",
                text_color=name_color
            )
            rank_label.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="w")

            # Name label
            name_label = ctk.CTkLabel(
                donor_row_frame,
                text=donor_name,
                font=ctk.CTkFont(size=font_size, weight=font_weight),
                anchor="w",
                text_color=name_color
            )
            name_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")


    def update_donor_data(self, new_donors):
        self._show_donors(new_donors) # Call _show_donors with new data
