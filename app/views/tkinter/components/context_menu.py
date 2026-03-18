import tkinter as tk


class ContextMenuHelper:
    def __init__(self, app):
        self.app = app

    def copy_to_clipboard(self):
        try:
            selected_text = self.app.url_entry.selection_get()
            if selected_text:
                self.app.clipboard_clear()
                self.app.clipboard_append(selected_text)
            else:
                self.app.add_log_message_safe(self.app.tr("No hay texto seleccionado para copiar."))
        except tk.TclError:
            self.app.add_log_message_safe(self.app.tr("No hay texto seleccionado para copiar."))

    def paste_from_clipboard(self):
        try:
            clipboard_text = self.app.clipboard_get()
            if clipboard_text:
                try:
                    self.app.url_entry.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                self.app.url_entry.insert(tk.INSERT, clipboard_text)
            else:
                self.app.add_log_message_safe(self.app.tr("No hay texto en el portapapeles para pegar."))
        except tk.TclError as e:
            self.app.add_log_message_safe(f"{self.app.tr('Error al pegar desde el portapapeles')}: {e}")

    def cut_to_clipboard(self):
        try:
            selected_text = self.app.url_entry.selection_get()
            if selected_text:
                self.app.clipboard_clear()
                self.app.clipboard_append(selected_text)
                self.app.url_entry.delete("sel.first", "sel.last")
            else:
                self.app.add_log_message_safe(self.app.tr("No hay texto seleccionado para cortar."))
        except tk.TclError:
            self.app.add_log_message_safe(self.app.tr("No hay texto seleccionado para cortar."))

    def show_context_menu(self, event):
        self.app.context_menu.tk_popup(event.x_root, event.y_root)
        self.app.context_menu.grab_release()