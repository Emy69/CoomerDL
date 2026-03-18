import customtkinter as ctk


class MenuHelpers:
    def __init__(self, app):
        self.app = app

    def toggle_archivo_menu(self):
        if self.app.archivo_menu_frame and self.app.archivo_menu_frame.winfo_exists():
            self.app.archivo_menu_frame.destroy()
        else:
            self.close_all_menus()
            self.app.archivo_menu_frame = self.create_menu_frame(
                [
                    (self.app.tr("Configuraciones"), self.app.settings_window.open_settings),
                    ("separator", None),
                    (self.app.tr("Salir"), self.app.quit),
                ],
                x=0
            )

    def create_menu_frame(self, options, x):
        menu_frame = ctk.CTkFrame(
            self.app,
            corner_radius=5,
            fg_color="gray25",
            border_color="black",
            border_width=1
        )
        menu_frame.place(x=x, y=30)
        menu_frame.configure(border_width=1, border_color="black")
        menu_frame.bind("<Button-1>", lambda e: "break")

        for option in options:
            if option[0] == "separator":
                separator = ctk.CTkFrame(menu_frame, height=1, fg_color="gray50")
                separator.pack(fill="x", padx=5, pady=5)
                separator.bind("<Button-1>", lambda e: "break")

            elif option[1] is None:
                label = ctk.CTkLabel(menu_frame, text=option[0], anchor="w", fg_color="gray30")
                label.pack(fill="x", padx=5, pady=2)
                label.bind("<Button-1>", lambda e: "break")

            else:
                btn = ctk.CTkButton(
                    menu_frame,
                    text=option[0],
                    fg_color="transparent",
                    hover_color="gray35",
                    anchor="w",
                    text_color="white",
                    command=lambda cmd=option[1]: cmd()
                )
                btn.pack(fill="x", padx=5, pady=2)
                btn.bind("<Button-1>", lambda e: "break")

        return menu_frame

    def close_all_menus(self):
        for menu_frame in [
            self.app.archivo_menu_frame,
            self.app.ayuda_menu_frame,
            self.app.donaciones_menu_frame
        ]:
            if menu_frame and menu_frame.winfo_exists():
                menu_frame.destroy()

    def get_all_children(self, widget):
        children = widget.winfo_children()
        all_children = list(children)
        for child in children:
            all_children.extend(self.get_all_children(child))
        return all_children

    def on_click(self, event):
        widgets_to_ignore = [self.app.menu_bar]

        for frame in [
            self.app.archivo_menu_frame,
            self.app.ayuda_menu_frame,
            self.app.donaciones_menu_frame
        ]:
            if frame and frame.winfo_exists():
                widgets_to_ignore.append(frame)
                widgets_to_ignore.extend(self.get_all_children(frame))

        if event.widget not in widgets_to_ignore:
            self.close_all_menus()