import tkinter as tk
from PIL import Image as PilImage, ImageTk
import customtkinter as ctk
import os

class PatchNotes:
    # Constants for window size and image path
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 759
    IMAGE_PATH = "resources/img/image.png"

    def __init__(self, parent, translations_func):
        """
        Initialize the PatchNotes class.
        
        :param parent: Parent widget, usually the main application window.
        :param translations_func: Function used to translate text into the user's language.
        """
        self.parent = parent
        self.tr = translations_func  # Translation function for multilingual support
        self.patch_notes_window = None  # This will hold the reference to the patch notes window

    def show_patch_notes(self):
        """
        Display the patch notes window. If the window is already open, it will bring it to the front.
        """
        # Check if the patch notes window already exists and is open
        if self.patch_notes_window is not None and tk.Toplevel.winfo_exists(self.patch_notes_window):
            self.patch_notes_window.lift()  # Bring the window to the front
            return
        
        # Create a new Toplevel window for patch notes
        self.patch_notes_window = ctk.CTkToplevel(self.parent)
        self.patch_notes_window.title(self.tr("<3"))
        self.patch_notes_window.transient(self.parent)  # Make it modal relative to the parent window
        self.patch_notes_window.grab_set()  # Block interactions with the parent window until this one is closed

        # Center the window on the screen
        self.center_window(self.patch_notes_window, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        # Main frame to hold the content of the patch notes
        main_frame = ctk.CTkFrame(self.patch_notes_window)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Retrieve and display the patch notes text
        patch_notes_text = self.get_patch_notes_text()
        patch_notes_content = ctk.CTkLabel(
            main_frame, 
            text=patch_notes_text, 
            justify="center",  # Center the text within the label
            wraplength=self.WINDOW_WIDTH - 40,  # Wrap text within the window's width minus some padding
            font=("Helvetica", 15)  # Set the font style and size
        )
        patch_notes_content.pack(pady=(20, 10))

        # Load and display the image (if available)
        self.load_image(main_frame)

        # Option for the user to not show the patch notes again (this could be linked to a preference)
        dont_show_again_var = tk.IntVar(value=0)
        
        # OK button to close the patch notes window
        ok_button = ctk.CTkButton(self.patch_notes_window, text=self.tr("OK"), command=lambda: self.close_patch_notes(dont_show_again_var))
        ok_button.pack(pady=10)

    def load_image(self, parent):
        """
        Load and display an image in the patch notes window, if the image file exists.
        
        :param parent: The parent widget where the image will be displayed.
        """
        if os.path.exists(self.IMAGE_PATH):
            try:
                # Open and resize the image using PIL
                pil_image = PilImage.open(self.IMAGE_PATH)
                pil_image = pil_image.resize((448, 398), PilImage.Resampling.LANCZOS)
                photo_image = ImageTk.PhotoImage(pil_image)
                
                # Display the image in a label widget
                image_label = tk.Label(parent, image=photo_image)
                image_label.image = photo_image  # Keep a reference to avoid garbage collection
                image_label.pack(pady=(10, 10))
            except Exception as e:
                # Handle any errors that occur during image loading
                print(f"Error loading image: {e}")
                error_label = ctk.CTkLabel(parent, text=self.tr("Failed to load the image."))
                error_label.pack(pady=(10, 10))
        else:
            # Handle the case where the image file is not found
            print(f"Image file not found: {self.IMAGE_PATH}")
            error_label = ctk.CTkLabel(parent, text=self.tr("Image file not found."))
            error_label.pack(pady=(10, 10))

    def center_window(self, window, width, height):
        """
        Center the window on the screen based on its dimensions.
        
        :param window: The window to be centered.
        :param width: The width of the window.
        :param height: The height of the window.
        """
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        window.geometry(f'{width}x{height}+{x}+{y}')

    def get_patch_notes_text(self):
        """
        Retrieve the patch notes text. This is where the patch notes content is defined.
        
        :return: A string containing the patch notes.
        """
        return self.tr("Thank you for all the support")

    def close_patch_notes(self, dont_show_again_var):
        """
        Close the patch notes window and optionally save the user's preference to not show it again.
        
        :param dont_show_again_var: A tkinter IntVar that indicates whether the patch notes should be shown again.
        """
        # Example: self.save_patch_notes_preference(not bool(dont_show_again_var.get()))  # Save the user's preference

        if self.patch_notes_window is not None:
            self.patch_notes_window.destroy()  # Destroy the patch notes window
            self.patch_notes_window = None  # Clear the reference to the window
