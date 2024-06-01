import tkinter as tk
from customtkinter import CTkToplevel, CTkLabel, CTkCheckBox, CTkButton, CTkFrame, set_appearance_mode, CTkScrollbar
import os
import webbrowser

set_appearance_mode("dark")

class PatchNotes:
    WINDOW_WIDTH = 950
    WINDOW_HEIGHT = 450
    PATCH_NOTES_PATH = "resources/config/patch_notes/patch_notes_pref.txt"
    PATCH_NOTES_DIR = "resources/config/patch_notes/versions/"

    def __init__(self, parent, translations_func):
        self.parent = parent
        self.tr = translations_func
        self.patch_notes = self.load_patch_notes()

    def load_patch_notes(self):
        patch_notes = {}
        for filename in os.listdir(self.PATCH_NOTES_DIR):
            if filename.endswith(".md"):
                with open(os.path.join(self.PATCH_NOTES_DIR, filename), "r", encoding="utf-8") as file:
                    version = filename.rsplit(".", 1)[0]
                    patch_notes[version] = {
                        "content": file.read()
                    }
        return patch_notes

    def show_patch_notes(self, auto_show=False):
        if auto_show and not self.should_show_patch_notes():
            return

        patch_notes_window = CTkToplevel(self.parent)
        patch_notes_window.title(self.tr("Notas de Parche"))
        self.configure_window_geometry(patch_notes_window)

        patch_notes_window.transient(self.parent)
        patch_notes_window.grab_set()

        
        version_listbox = tk.Listbox(
            patch_notes_window, 
            bg="#2B2B2B", 
            fg="white", 
            highlightthickness=0, 
            selectbackground="#505050", 
            selectforeground="white",
            font=("Helvetica", 14)
        )
        version_listbox.pack(side="left", fill="y", padx=10, pady=10)

        
        for version in sorted(self.patch_notes.keys(), reverse=True):
            version_listbox.insert("end", version)

       
        content_frame = CTkFrame(patch_notes_window)
        content_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # Create a Text widget for patch notes content with a Scrollbar
        text_frame = CTkFrame(content_frame)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.patch_notes_content = tk.Text(text_frame, wrap="word", bg="#2B2B2B", fg="white", font=("Helvetica", 12), relief="flat")
        scrollbar = CTkScrollbar(text_frame, command=self.patch_notes_content.yview)
        self.patch_notes_content.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.patch_notes_content.pack(side="left", fill="both", expand=True)

        # Add tag configuration for hyperlinks
        self.patch_notes_content.tag_configure("hyperlink", foreground="blue", underline=True)
        self.patch_notes_content.tag_bind("hyperlink", "<Enter>", lambda e: self.patch_notes_content.config(cursor="hand2"))
        self.patch_notes_content.tag_bind("hyperlink", "<Leave>", lambda e: self.patch_notes_content.config(cursor=""))
        self.patch_notes_content.tag_bind("hyperlink", "<Button-1>", lambda e: self.open_url(e))

        # Set default patch notes content to the latest version
        self.update_patch_notes_content(event=None, listbox=version_listbox)

        # Update content when a new version is selected
        version_listbox.bind("<<ListboxSelect>>", lambda event: self.update_patch_notes_content(event, version_listbox))

        # Create a frame for the control buttons
        control_frame = CTkFrame(patch_notes_window)
        control_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        dont_show_again_var = tk.IntVar(value=0)
        dont_show_again_check = CTkCheckBox(control_frame, text=self.tr("No_mostrar"), variable=dont_show_again_var)
        dont_show_again_check.pack(side="left", padx=10)

        ok_button = CTkButton(control_frame, text=self.tr("OK"), command=lambda: self.close_patch_notes(patch_notes_window, dont_show_again_var))
        ok_button.pack(side="right", padx=10)

    def configure_window_geometry(self, window):
        position_right = int(self.parent.winfo_x() + (self.parent.winfo_width() / 2) - (self.WINDOW_WIDTH / 2))
        position_down = int(self.parent.winfo_y() + (self.parent.winfo_height() / 2) - (self.WINDOW_HEIGHT / 2))
        window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{position_right}+{position_down}")

    def update_patch_notes_content(self, event=None, listbox=None):
        if event:
            listbox = event.widget
            selection = listbox.curselection()
            if selection:
                version = listbox.get(selection[0])
                self.display_patch_notes(version)
        elif listbox:
            version = sorted(self.patch_notes.keys(), reverse=True)[0]
            self.display_patch_notes(version)

    def display_patch_notes(self, version):
        self.patch_notes_content.config(state="normal")  
        self.patch_notes_content.delete("1.0", tk.END)
        version_info = self.patch_notes[version]
        md_text = version_info["content"]
        self.patch_notes_content.insert(tk.END, "-" * 100 + "\n", "separator")
        self.render_markdown(md_text)
        self.patch_notes_content.insert(tk.END, "\n" + "-" * 100 + "\n", "separator")
        self.patch_notes_content.config(state="disabled")  

    def render_markdown(self, text):
        lines = text.split("\n")
        for line in lines:
            if line.startswith("# "):
                self.insert_header(line[2:] + "\n\n", 1)
            elif line.startswith("## "):
                self.insert_header(line[3:] + "\n\n", 2)
            elif line.startswith("- "):
                if "[" in line and "]" in line and "(" in line and ")" in line:
                    link_text = line[line.index("[") + 1:line.index("]")]
                    url = line[line.index("(") + 1:line.index(")")]
                    self.insert_hyperlink("• " + link_text + "\n", url)
                else:
                    self.patch_notes_content.insert(tk.END, "• " + line[2:] + "\n")
            else:
                self.patch_notes_content.insert(tk.END, line + "\n")

    def insert_header(self, text, level):
        start_index = self.patch_notes_content.index(tk.END)
        self.patch_notes_content.insert(tk.END, text)
        end_index = self.patch_notes_content.index(tk.END)
        font_size = 16 if level == 1 else 14
        self.patch_notes_content.tag_add(f"header{level}", start_index, end_index)

    def insert_hyperlink(self, text, url):
        start_index = self.patch_notes_content.index(tk.END)
        self.patch_notes_content.insert(tk.END, text)
        end_index = self.patch_notes_content.index(tk.END)
        self.patch_notes_content.tag_add("hyperlink", start_index, end_index)
        self.patch_notes_content.tag_bind("hyperlink", "<Button-1>", lambda e, url=url: self.open_url(url))

    def open_url(self, url):
        webbrowser.open(url)

    def close_patch_notes(self, window, dont_show_again_var):
        self.save_patch_notes_preference(not bool(dont_show_again_var.get()))
        window.destroy()

    def save_patch_notes_preference(self, show_again):
        os.makedirs(os.path.dirname(self.PATCH_NOTES_PATH), exist_ok=True)
        with open(self.PATCH_NOTES_PATH, "w") as f:
            f.write(str(show_again))
    def should_show_patch_notes(self):
        try:
            with open(self.PATCH_NOTES_PATH, "r") as f:
                return f.read().strip().lower() in ['true', '1', 't', 'y', 'yes']
        except Exception as e:
            print(f"Error reading patch notes preferences: {e}")
            return True