import customtkinter as ctk
import requests
import threading
import json

class DonorsModal(ctk.CTkToplevel):
    def __init__(self, parent, tr):
        super().__init__(parent)
        self.parent = parent
        self.tr = tr # Translation function
        
        self.title(self.tr("Donors Leaderboard"))
        self.geometry("400x500")
        self.resizable(False, False)
        self.transient(parent)
        self.after_idle(self.grab_set)
        
        self.center_window()
        self.create_ui()
        
        # Start loading data in a separate thread to prevent UI freeze
        threading.Thread(target=self._load_donors, daemon=True).start()

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
            text=self.tr("Donors"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        self.donors_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        self.donors_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.donors_frame.grid_columnconfigure(0, weight=0) # For rank
        self.donors_frame.grid_columnconfigure(1, weight=1) # For name
        self.donors_frame.grid_columnconfigure(2, weight=0) # For amount

        self.status_label = ctk.CTkLabel(
            self.donors_frame,
            text=self.tr("Loading donors..."),
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.status_label.pack(pady=20)

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
                'https://emydev.com/coomer/donadores.php',
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
        self.status_label.pack_forget()

        # Clear existing data
        for widget in self.donors_frame.winfo_children():
            widget.destroy()

        if not donors:
            ctk.CTkLabel(self.donors_frame, text=self.tr("No donors found.")).pack(pady=20)
            return

        # Sort by amount in descending order, ensuring numeric comparison
        donors.sort(key=lambda x: float(x.get("donated_amount", 0)) if isinstance(x.get("donated_amount"), (int, float, str)) and str(x.get("donated_amount")).replace('.', '', 1).isdigit() else 0.0, reverse=True)

        for i, donor in enumerate(donors):
            donor_name = donor.get("name", self.tr("Unknown Donor"))
            try:
                donated_amount = float(donor.get("donated_amount", 0))
            except (ValueError, TypeError):
                donated_amount = 0.0

            # Determine styling based on rank
            rank_text = f"#{i+1}"
            font_size = 14
            font_weight = "normal"
            name_color = "white"
            amount_color = "#FFC107"
            row_bg_color = "transparent"
            rank_icon = ""

            if i == 0:
                rank_icon = "🥇"
                font_size = 18
                font_weight = "bold"
                name_color = "#FFD700"
                amount_color = "#FFD700"
                row_bg_color = "#3a3a2a"
            elif i == 1:
                rank_icon = "🥈"
                font_size = 16
                font_weight = "bold"
                name_color = "#C0C0C0"
                amount_color = "#C0C0C0"
                row_bg_color = "#303030"
            elif i == 2:
                rank_icon = "🥉"
                font_size = 15
                font_weight = "bold"
                name_color = "#CD7F32"
                amount_color = "#CD7F32"
                row_bg_color = "#2a2a2a"
            else:
                amount_color = "#4CAF50" if donated_amount >= 1000 else "#FFC107"

            donor_row_frame = ctk.CTkFrame(self.donors_frame, fg_color=row_bg_color, corner_radius=8)
            donor_row_frame.pack(fill="x", pady=4, padx=5) # Add more padding
            donor_row_frame.grid_columnconfigure(0, weight=0) # Rank icon/text
            donor_row_frame.grid_columnconfigure(1, weight=1) # Name
            donor_row_frame.grid_columnconfigure(2, weight=0) # Amount

            # Rank label with icon
            rank_label = ctk.CTkLabel(
                donor_row_frame,
                text=f"{rank_icon} {rank_text}",
                font=ctk.CTkFont(size=font_size, weight=font_weight),
                width=60, # Increased width for icon
                anchor="w",
                text_color=name_color if i < 3 else "white" # Rank text color
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

            # Amount label
            amount_label = ctk.CTkLabel(
                donor_row_frame,
                text=f"${donated_amount:,.2f}",
                font=ctk.CTkFont(size=font_size, weight="bold"),
                text_color=amount_color,
                anchor="e"
            )
            amount_label.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="e")

    def update_donor_data(self, new_donors):
        self._show_donors(new_donors) # Call _show_donors with new data
