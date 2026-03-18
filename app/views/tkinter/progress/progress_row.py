import customtkinter as ctk

from app.views.tkinter.progress.progress_utils import (
    get_file_icon_key,
    shorten_filename,
    format_eta,
    format_progress_text,
)


class ProgressRow:
    def __init__(self, parent, icons, progress_item):
        self.parent = parent
        self.icons = icons
        self.progress_item = progress_item

        icon_key = get_file_icon_key(progress_item.file_path)
        icon = self.icons.get(icon_key, self.icons.get("default"))

        self.frame = ctk.CTkFrame(parent)
        self.frame.pack(fill="x", padx=5, pady=5)

        self.icon_and_text_frame = ctk.CTkFrame(self.frame)
        self.icon_and_text_frame.pack(side="left", padx=5)

        self.icon_label = ctk.CTkLabel(self.icon_and_text_frame, image=icon, text="")
        self.icon_label.pack(side="left")

        self.progress_label = ctk.CTkLabel(
            self.icon_and_text_frame,
            text=shorten_filename(progress_item.file_path),
            anchor="w"
        )
        self.progress_label.pack(side="left", padx=5)

        self.progress_bar = ctk.CTkProgressBar(self.frame)
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        self.percentage_label = ctk.CTkLabel(self.frame, text="0%")
        self.percentage_label.pack(side="left", padx=5)

        self.eta_label = ctk.CTkLabel(self.frame, text="ETA: N/A")
        self.eta_label.pack(side="right", padx=5)

    def update(self, progress_item):
        self.progress_item = progress_item

        downloaded = progress_item.downloaded
        total = progress_item.total
        eta = progress_item.eta

        if total > 0:
            self.progress_bar.set(downloaded / total)
        else:
            self.progress_bar.set(0)

        self.percentage_label.configure(text=format_progress_text(downloaded, total))
        self.eta_label.configure(text=format_eta(eta))

    def destroy_later(self, delay_ms=2000, callback=None):
        self.frame.after(delay_ms, lambda: self._destroy(callback))

    def _destroy(self, callback=None):
        if self.frame.winfo_exists():
            self.frame.pack_forget()
            self.frame.destroy()
        if callback:
            callback()