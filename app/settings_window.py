import json
import os
import sqlite3
import threading
import requests
import customtkinter as ctk
import tkinter as tk
import requests
from PIL import Image, ImageTk
from PIL import Image as PilImage
from tkinter import filedialog, messagebox, ttk
from app.services.settings_window_service import SettingsWindowService
from app.services.download_settings_service import DownloadSettingsService
from app.services.database_settings_service import DatabaseSettingsService

class SettingsWindow:
    CONFIG_PATH = 'resources/config/settings.json' 

    def __init__(self, parent, translate, load_translations_func, update_ui_texts_func, save_language_preference_func, version, downloader, check_for_new_version_func,on_settings_changed=None):
        self.parent = parent
        self.translate = translate
        self.load_translations = load_translations_func
        self.update_ui_texts = update_ui_texts_func
        self.save_language_preference = save_language_preference_func
        self.version = version
        self.downloader = downloader
        self.check_for_new_version = check_for_new_version_func
        self.languages = {
            "Español": "es",
            "English": "en",
            "日本語": "ja",
            "中文": "zh",
            "Français": "fr",
            "Русский": "ru"
        }

        self.settings_service = SettingsWindowService(
            config_path=self.CONFIG_PATH,
            on_settings_changed=on_settings_changed
        )
        self.download_settings_service = DownloadSettingsService()
        self.database_settings_service = DatabaseSettingsService()
        self.settings = self.settings_service.load_settings()
        self.folder_structure_icons = self.load_icons()
        self.site_status_labels = {}
        self.site_textboxes = {} 

    def load_settings(self):
        return self.settings_service.load_settings()

    def save_settings(self):
        self.settings_service.save_settings(self.settings)
        
    def load_icons(self):
        icons = {}
        try:
            icons['folder'] = ImageTk.PhotoImage(PilImage.open("resources/img/iconos/settings/folder.png").resize((20, 20), PilImage.Resampling.LANCZOS))
        except Exception as e:
            messagebox.showerror(self.translate("Error"), self.translate(f"Error loading icons: {e}"))
            icons['folder'] = None
        return icons

    def open_settings(self):
        self.settings_window = ctk.CTkToplevel(self.parent)
        self.settings_window.title(self.translate("Settings"))
        self.settings_window.geometry("800x600")
        self.settings_window.transient(self.parent)
        self.settings_window.deiconify()
        self.settings_window.after_idle(self.settings_window.grab_set)
        self.center_window(self.settings_window, 800, 600)
        self.main_frame = ctk.CTkFrame(self.settings_window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabview = ctk.CTkTabview(self.main_frame, width=700, height=500)
        self.tabview.pack(fill="both", expand=True)
        # Existing tabs
        self.general_tab = self.tabview.add(self.translate("General"))
        self.downloads_tab = self.tabview.add(self.translate("Downloads"))
        self.structure_tab = self.tabview.add(self.translate("Structure"))
        self.db_tab = self.tabview.add(self.translate("Database"))
        self.cookies_tab = self.tabview.add(self.translate("Cookies"))
        
        # New tab for database
        self.render_general_tab(self.general_tab)
        self.render_downloads_tab(self.downloads_tab)
        self.render_structure_tab(self.structure_tab)
        self.render_db_tab(self.db_tab)
        self.render_cookies_tab(self.cookies_tab)
    
    def render_db_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        db_frame = ctk.CTkFrame(tab, fg_color="transparent")
        db_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header_label = ctk.CTkLabel(db_frame, text=self.translate("Database Management"), font=("Helvetica", 16, "bold"))
        header_label.pack(pady=(0, 10))
        
        # Configurar un estilo personalizado para el Treeview
        style = ttk.Style()
        style.theme_use('clam')  # O puedes elegir 'default' o 'alt'
        style.configure("Custom.Treeview",
                        background="#2e2e2e",
                        foreground="white",
                        fieldbackground="#2e2e2e",
                        rowheight=25,
                        font=('Helvetica', 10))
        style.configure("Custom.Treeview.Heading",
                        background="#1e1e1e",
                        foreground="white",
                        font=('Helvetica', 10, 'bold'))
        # Para filas alternas (opcional)
        style.map("Custom.Treeview", background=[("selected", "#4a6984")])
        
        # Frame para el Treeview y su scrollbar
        table_frame = tk.Frame(db_frame)
        table_frame.pack(fill="both", expand=True)
        
        # Definir las columnas que se mostrarán en la parte derecha del Treeview
        columns = ("id", "file_name", "type", "size", "downloaded_at")
        self.db_tree = ttk.Treeview(table_frame, style="Custom.Treeview", columns=columns, show="tree headings", height=15, selectmode="extended")
        
        # Configurar encabezados
        self.db_tree.heading("#0", text=self.translate("User/Post"), anchor="w")
        self.db_tree.heading("id", text="ID", anchor="center")
        self.db_tree.heading("file_name", text=self.translate("File Name"), anchor="w")
        self.db_tree.heading("type", text=self.translate("Type"), anchor="center")
        self.db_tree.heading("size", text=self.translate("Size"), anchor="center")
        self.db_tree.heading("downloaded_at", text=self.translate("Downloaded At"), anchor="center")
        
        # Configurar ancho de columnas
        self.db_tree.column("#0", width=180)
        self.db_tree.column("id", width=30, anchor="center")
        self.db_tree.column("file_name", width=200)
        self.db_tree.column("type", width=80, anchor="center")
        self.db_tree.column("size", width=80, anchor="center")
        self.db_tree.column("downloaded_at", width=150, anchor="center")
        
        # Scrollbar vertical
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=vsb.set)
        self.db_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Botones para exportar y limpiar
        btn_frame = ctk.CTkFrame(db_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        export_button = ctk.CTkButton(btn_frame, text=self.translate("Export Database"), command=self.export_db)
        export_button.pack(side="left", padx=10)
        clear_button = ctk.CTkButton(btn_frame, text=self.translate("Clear Database"), command=self.clear_db)
        clear_button.pack(side="left", padx=10)
        
        delete_users_button = ctk.CTkButton(
            btn_frame,
            text=self.translate("Delete Selected Users"),
            command=self.delete_selected_users
        )
        delete_users_button.pack(side="left", padx=10)
        
        # Cargar los registros en el Treeview con agrupación por usuario y post
        self.load_db_records()
        
    def render_cookies_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Cookie Management",
            font=("Helvetica", 18, "bold")
        )
        title_label.pack(anchor="w")

        desc_label = ctk.CTkLabel(
            header_frame,
            text="Paste or import cookies in JSON format (list of objects with name, value, domain, path). "
                "They will be stored by site in resources/config/cookies/{sitio}.json",
            font=("Helvetica", 12),
            text_color="gray",
            wraplength=800,
            justify="left"
        )
        desc_label.pack(anchor="w", pady=(5, 0))

        main_frame = ctk.CTkScrollableFrame(tab)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_frame.grid_columnconfigure(0, weight=1)

        sites_config = [
            {"key": "simpcity", "name": "SimpCity", "color": "#FF6B6B", "icon": "🌐",
            "description": "Cookies for accessing SimCity"},
        ]

        def cookie_path_for(site_key: str) -> str:
            base = "resources/config/cookies"
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, f"{site_key}.json")

        for i, cfg in enumerate(sites_config):
            site_key  = cfg["key"]
            site_name = cfg["name"]
            site_color = cfg["color"]
            site_icon = cfg["icon"]
            site_desc = cfg["description"]

            # --- Container ---
            site_container = ctk.CTkFrame(main_frame)
            site_container.grid(row=i, column=0, sticky="ew", pady=(0, 22), padx=10)
            site_container.grid_columnconfigure(0, weight=1)

            accent = ctk.CTkFrame(site_container, height=4, fg_color=site_color)
            accent.grid(row=0, column=0, sticky="ew")

            # Header
            header = ctk.CTkFrame(site_container, fg_color="transparent")
            header.grid(row=1, column=0, sticky="ew", padx=15, pady=(10, 6))
            header.grid_columnconfigure(1, weight=1)

            title = ctk.CTkLabel(header, text=f"{site_icon} {site_name}", font=("Helvetica", 16, "bold"))
            title.grid(row=0, column=0, sticky="w")

            status_exists = os.path.exists(cookie_path_for(site_key))
            status_label = ctk.CTkLabel(
                header,
                text=("✓ Configuradas" if status_exists else "⚠ Sin configurar"),
                font=("Helvetica", 11),
                text_color=("#4CAF50" if status_exists else "#FF9800")
            )
            status_label.grid(row=0, column=1, sticky="e")
            self.site_status_labels[site_key] = status_label

            if site_desc:
                desc = ctk.CTkLabel(
                    header, text=site_desc, font=("Helvetica", 11),
                    text_color="gray", wraplength=600, justify="left"
                )
                desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
                
            instructions_frame = ctk.CTkFrame(site_container, fg_color=("gray90", "gray20"))
            instructions_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 8))
            instructions = (
                "📋 How to obtain cookies (JSON format):\n"
                "1) Open the browser Developer Tools (F12).\n"
                "2) Go to Application/Storage → Cookies and select the site.\n"
                "3) Use an extension to export cookies as JSON (e.g., EditThisCookie), or copy the fields manually.\n"
                "4) Paste the JSON below or import a .json file.\n"
                "   Expected format: an array of objects with at least name, value, domain, path."
            )
            ctk.CTkLabel(instructions_frame, text=instructions, font=("Helvetica", 10),
                        justify="left", anchor="w").pack(padx=12, pady=8, fill="x")

            # Textbox
            text_frame = ctk.CTkFrame(site_container, fg_color="transparent")
            text_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(2, 6))
            text_frame.grid_columnconfigure(0, weight=1)

            textbox = ctk.CTkTextbox(text_frame, height=160, wrap="none")
            textbox.grid(row=0, column=0, sticky="ew")

            pre_path = cookie_path_for(site_key)
            if os.path.exists(pre_path):
                try:
                    with open(pre_path, "r", encoding="utf-8") as f:
                        textbox.delete("1.0", "end")
                        textbox.insert("1.0", f.read())
                except Exception:
                    pass
            self.site_textboxes[site_key] = textbox

            buttons = ctk.CTkFrame(site_container, fg_color="transparent")
            buttons.grid(row=4, column=0, sticky="ew", padx=15, pady=(4, 12))
            buttons.grid_columnconfigure((0,1,2,3), weight=0)
            buttons.grid_columnconfigure(4, weight=1)

            def do_import(sk=site_key, tb=textbox):
                file = filedialog.askopenfilename(
                    title=f"Import cookies JSON for {sk}",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if not file:
                    return
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read()
                    json.loads(content)  # valida
                    tb.delete("1.0", "end")
                    tb.insert("1.0", content)
                    messagebox.showinfo("OK", f"Cookies loaded into editor for {sk}. Don't forget to Save!")
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid JSON: {e}")

            def do_save(sk=site_key, tb=textbox, sl=status_label):
                content = tb.get("1.0", "end").strip()
                if not content:
                    messagebox.showwarning("Empty", "Nothing to save.")
                    return
                try:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        data = [data]
                    if not isinstance(data, list):
                        raise ValueError("JSON must be an object or an array of objects.")
                    for idx, c in enumerate(data, start=1):
                        if not isinstance(c, dict) or "name" not in c or "value" not in c:
                            raise ValueError(f"Item {idx} is missing 'name' or 'value'.")
                    save_path = cookie_path_for(sk)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    sl.configure(text="✓ Configured", text_color="#4CAF50")
                    messagebox.showinfo("OK", f"Cookies saved to:\n{save_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save: {e}")

            def do_test(sk=site_key, sl=status_label):
                urls = {
                    "simpcity": ["https://www.simpcity.cr/"]
                }
                test_path = cookie_path_for(sk)
                if not os.path.exists(test_path):
                    messagebox.showwarning("Missing file", "You haven't saved cookies for this site yet.")
                    return
                try:
                    with open(test_path, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    s = requests.Session()
                    jar = requests.cookies.RequestsCookieJar()
                    for c in cookies if isinstance(cookies, list) else [cookies]:
                        jar.set(c["name"], c["value"], domain=c.get("domain", None), path=c.get("path", "/"))
                    s.cookies = jar
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                    }
                    ok_any, codes = False, []
                    for test_url in urls.get(sk, []):
                        try:
                            r = s.get(test_url, headers=headers, timeout=12)
                            codes.append(r.status_code)
                            if 200 <= r.status_code < 400:
                                ok_any = True
                        except Exception:
                            codes.append("ERR")
                    if ok_any:
                        sl.configure(text="✓ Configured (test OK)", text_color="#4CAF50")
                        messagebox.showinfo("OK", f"Response from {sk}: {codes}")
                    else:
                        sl.configure(text="⚠ Tested (non-OK response)", text_color="#FFC107")
                        messagebox.showwarning("Heads up", f"Response from {sk}: {codes}\n"
                            "Cookie format looks fine but the site returned non-OK status codes.\n"
                            "If content requires login, try a protected URL inside the downloader.")
                except Exception as e:
                    sl.configure(text="⚠ Not configured", text_color="#FF9800")
                    messagebox.showerror("Error", f"Test failed: {e}")

            def do_clear(sk=site_key, tb=textbox, sl=status_label):
                del_path = cookie_path_for(sk)
                if os.path.exists(del_path):
                    try:
                        os.remove(del_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete file: {e}")
                        return
                tb.delete("1.0", "end")
                sl.configure(text="⚠ Not configured", text_color="#FF9800")
                messagebox.showinfo("OK", f"Cookies for {sk} deleted.")

            ctk.CTkButton(buttons, text="Import JSON...", command=do_import).grid(row=0, column=0, padx=(0, 6))
            ctk.CTkButton(buttons, text="Save",command=do_save).grid(   row=0, column=1, padx=6)
            ctk.CTkButton(buttons, text="Test",command=do_test).grid(   row=0, column=2, padx=6)
            ctk.CTkButton(buttons, text="Delete",command=do_clear, fg_color="#E53935", hover_color="#C62828").grid(row=0, column=3, padx=6)
    
    def delete_selected_users(self):
        selected = self.db_tree.selection()
        if not selected:
            messagebox.showwarning(
                self.translate("Warning"),
                self.translate("Please select at least one user to delete.")
            )
            return

        user_ids = [
            self.db_tree.item(node, 'text')
            for node in selected
            if self.db_tree.parent(node) == ''
        ]
        if not user_ids:
            messagebox.showwarning(
                self.translate("Warning"),
                self.translate("Please select valid user entries (not posts/files).")
            )
            return

        confirm = messagebox.askyesno(
            self.translate("Confirm"),
            self.translate(
                "Are you sure you want to delete all records for user(s): {}?".format(
                    ", ".join(user_ids)
                )
            )
        )
        if not confirm:
            return

        try:
            self.database_settings_service.delete_users(self.downloader.db_path, user_ids)
            messagebox.showinfo(
                self.translate("Success"),
                self.translate("Selected user(s) and their records were deleted.")
            )
            self.load_db_records()
        except Exception as e:
            messagebox.showerror(
                self.translate("Error"),
                self.translate(f"Error deleting user(s): {e}")
            )


    def load_db_records(self):
        db_path = self.downloader.db_path

        if not self.database_settings_service.database_exists(db_path):
            tk.messagebox.showwarning(
                self.translate("Warning"),
                self.translate("Database not found.")
            )
            return

        try:
            rows = self.database_settings_service.fetch_download_rows(db_path)
        except Exception as e:
            tk.messagebox.showerror(
                self.translate("Error"),
                self.translate("Error loading database: {e}", e=e)
            )
            return

        for child in self.db_tree.get_children():
            self.db_tree.delete(child)

        payload = self.database_settings_service.build_tree_payload(rows)

        for user_entry in payload:
            user = user_entry["user"]
            user_node = self.db_tree.insert("", "end", text=user, open=False)

            for post, items in user_entry["posts"].items():
                post_node = self.db_tree.insert(user_node, "end", text=post, open=False)
                for item in items:
                    self.db_tree.insert(
                        post_node,
                        "end",
                        values=(
                            item["id"],
                            item["file_name"],
                            self.translate(item["file_type"]),
                            item["size_str"],
                            item["downloaded_at"],
                        )
                    )

            if user_entry["no_post"]:
                no_post_node = self.db_tree.insert(
                    user_node,
                    "end",
                    text=self.translate("No Post"),
                    open=False
                )
                for item in user_entry["no_post"]:
                    self.db_tree.insert(
                        no_post_node,
                        "end",
                        values=(
                            item["id"],
                            item["file_name"],
                            self.translate(item["file_type"]),
                            item["size_str"],
                            item["downloaded_at"],
                        )
                    )

    def render_general_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)

        # General frame
        general_frame = ctk.CTkFrame(tab, fg_color="transparent")
        general_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        general_frame.grid_columnconfigure(1, weight=1)

        # Main label
        general_label = ctk.CTkLabel(general_frame, text=self.translate("General Options"), font=("Helvetica", 16, "bold"))
        general_label.grid(row=0, column=0, columnspan=3, sticky="w")

        # Section description
        description_label = ctk.CTkLabel(general_frame, text=self.translate("Here you can change the appearance and language of the application."), 
                                         font=("Helvetica", 11), text_color="gray")
        description_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # Theme
        theme_label = ctk.CTkLabel(general_frame, text=self.translate("Theme"), font=("Helvetica", 14))
        theme_label.grid(row=2, column=0, pady=5, sticky="w")

        theme_combobox = ctk.CTkComboBox(general_frame, values=["Light", "Dark", "System"], state='readonly', width=120)
        theme_combobox.set(self.settings.get('theme', 'System'))
        theme_combobox.grid(row=2, column=1, pady=5, padx=(10,0), sticky="w")

        apply_theme_button = ctk.CTkButton(general_frame, text=self.translate("Apply Theme"), 
                                           command=lambda: self.change_theme_in_thread(theme_combobox.get()))
        apply_theme_button.grid(row=2, column=2, pady=5, sticky="e")

        # Separator
        separator_1 = ttk.Separator(general_frame, orient="horizontal")
        separator_1.grid(row=3, column=0, columnspan=3, sticky="ew", pady=15)

        # Language
        language_label = ctk.CTkLabel(general_frame, text=self.translate("Language"), font=("Helvetica", 14))
        language_label.grid(row=4, column=0, pady=5, sticky="w")

        language_combobox = ctk.CTkComboBox(general_frame, values=list(self.languages.keys()), state='readonly', width=120)
        language_combobox.set(self.get_language_name(self.settings.get('language', 'en')))
        language_combobox.grid(row=4, column=1, pady=5, padx=(10,0), sticky="w")

        apply_language_button = ctk.CTkButton(general_frame, text=self.translate("Apply Language"),
                                              command=lambda: self.apply_language_settings(language_combobox.get()))
        apply_language_button.grid(row=4, column=2, pady=5, sticky="e")

        # Separator for updates
        separator_2 = ttk.Separator(general_frame, orient="horizontal")
        separator_2.grid(row=5, column=0, columnspan=3, sticky="ew", pady=15)

        # Check for Updates
        update_label = ctk.CTkLabel(general_frame, text=self.translate("Check for Updates"), font=("Helvetica", 14))
        update_label.grid(row=6, column=0, pady=5, sticky="w")

        check_update_button = ctk.CTkButton(general_frame, text=self.translate("Check Now"),
                                            command=lambda: threading.Thread(target=self.check_for_new_version, args=(False,)).start())
        check_update_button.grid(row=6, column=1, pady=5, padx=(10,0), sticky="w")


    def render_downloads_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Frame for the "Downloads" tab
        downloads_frame = ctk.CTkFrame(tab, fg_color="transparent")
        downloads_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        downloads_frame.grid_columnconfigure(1, weight=1)

        download_label = ctk.CTkLabel(downloads_frame, text=self.translate("Download Options"), font=("Helvetica", 16, "bold"))
        download_label.grid(row=0, column=0, columnspan=2, sticky="w")

        description_label = ctk.CTkLabel(
            downloads_frame,
            text=self.translate("Here you can adjust the number of simultaneous downloads, file naming, retries, and more."),
            font=("Helvetica", 11),
            text_color="gray"
        )
        description_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 15))


        # ----------------------------
        # Simultaneous downloads
        # ----------------------------
        max_downloads_label = ctk.CTkLabel(downloads_frame, text=self.translate("Simultaneous Downloads"))
        max_downloads_label.grid(row=2, column=0, pady=5, sticky="w")

        max_downloads_combobox = ctk.CTkComboBox(
            downloads_frame,
            values=[str(i) for i in range(1, 11)],
            state='readonly',
            width=80
        )
        max_downloads_combobox.set(str(self.settings.get('max_downloads', 3)))
        max_downloads_combobox.grid(row=2, column=1, pady=5, padx=(10, 0), sticky="w")


        # ----------------------------
        # Folder structure
        # ----------------------------
        folder_structure_label = ctk.CTkLabel(downloads_frame, text=self.translate("Folder Structure"))
        folder_structure_label.grid(row=3, column=0, pady=5, sticky="w")

        folder_structure_combobox = ctk.CTkComboBox(
            downloads_frame,
            values=["default", "post_number"],
            state='readonly',
            width=150
        )
        folder_structure_combobox.set(self.settings.get('folder_structure', 'default'))
        folder_structure_combobox.grid(row=3, column=1, pady=5, padx=(10, 0), sticky="w")


        # ----------------------------
        # Max retries
        # ----------------------------
        retry_label = ctk.CTkLabel(downloads_frame, text=self.translate("Max Retries"))
        retry_label.grid(row=4, column=0, pady=5, sticky="w")

        retry_combobox = ctk.CTkComboBox(
            downloads_frame,
            values=[str(i) for i in range(0, 11)] + ['999999'],
            state='readonly',
            width=80
        )
        retry_combobox.set(str(self.settings.get('max_retries', 3)))
        retry_combobox.grid(row=4, column=1, pady=5, padx=(10, 0), sticky="w")


        # ----------------------------
        # Retry interval
        # ----------------------------
        retry_interval_label = ctk.CTkLabel(downloads_frame, text=self.translate("Retry Interval (seconds)"))
        retry_interval_label.grid(row=5, column=0, pady=5, sticky="w")

        retry_interval_entry = ctk.CTkEntry(downloads_frame, width=80)
        retry_interval_entry.insert(0, str(self.settings.get('retry_interval', 2.0)))
        retry_interval_entry.grid(row=5, column=1, pady=5, padx=(10, 0), sticky="w")


        # ----------------------------
        # File naming mode
        # ----------------------------
        naming_label = ctk.CTkLabel(downloads_frame, text=self.translate("File Naming Mode"))
        naming_label.grid(row=6, column=0, pady=5, sticky="w")

        naming_options = self.download_settings_service.get_naming_options()

        file_naming_combobox = ctk.CTkComboBox(
            downloads_frame,
            values=naming_options,
            state='readonly',
            width=200
        )

        current_naming_label = self.download_settings_service.get_naming_label_from_setting(
            self.settings.get("file_naming_mode", 0)
        )
        file_naming_combobox.set(current_naming_label)
        file_naming_combobox.grid(row=6, column=1, pady=5, padx=(10, 0), sticky="w")


        # ----------------------------
        # Botón para aplicar configuración
        # ----------------------------
        apply_download_button = ctk.CTkButton(
            downloads_frame,
            text=self.translate("Apply Download Settings"),
            command=lambda: self.apply_download_settings(
                max_downloads_combobox,
                folder_structure_combobox,
                retry_combobox,
                retry_interval_entry,
                file_naming_combobox
            )
        )
        apply_download_button.grid(row=7, column=1, pady=10, sticky="e")



    def render_structure_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        structure_label = ctk.CTkLabel(
            tab,
            text=self.translate("Folder Structure Preview"),
            font=("Helvetica", 16, "bold")
        )
        structure_label.grid(row=0, column=0, pady=(20,10), sticky="w")

        # Descripción principal
        description_label = ctk.CTkLabel(
            tab,
            text=self.translate("Here you can see how your downloaded files will be organized on disk."),
            font=("Helvetica", 11),
            text_color="gray"
        )
        description_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0,15))

        # -------- BLOQUE DE EJEMPLO: Ejemplos de nombres de archivos según la opción --------
        examples_text = (
            "Ejemplos de nombres según File Naming Mode:\n\n"
            " • [Modo 0] Use File ID (default):  \n"
            "     123456.mp4  (usa el nombre/ID original del archivo)\n\n"
            " • [Modo 1] Use Sanitized Post Name:  \n"
            "     Mi_Post_Ejemplo_1_ab12.mp4  (nombre del post + índice del adjunto + hash único)\n\n"
            " • [Modo 2] Post Name + Post ID Suffix:  \n"
            "     Mi_Post_Ejemplo - 98765_1.mp4  (nombre del post + ID del post + índice del adjunto)\n"
            " • [Modo 3] Post Time + Post Name:  \n"
            "     2000-01-01T00_00_00 - Mi_Post_Ejemplo - 98765_1.mp4  (post date/time + nombre del post + índice del adjunto + hash único)\n"
        )
        examples_label = ctk.CTkLabel(
            tab,
            text=self.translate(examples_text),
            font=("Helvetica", 11),
            text_color="gray",
            justify="left"
        )
        examples_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0,15))
        # ------------------------------------------------------------------------------------

        treeview_frame = ctk.CTkFrame(tab, fg_color="transparent")
        treeview_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=20)
        treeview_frame.grid_rowconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(1, weight=1)

        self.default_treeview = ttk.Treeview(treeview_frame, show="tree")
        self.default_treeview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.post_treeview = ttk.Treeview(treeview_frame, show="tree")
        self.post_treeview.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.update_treeview()
    
    def export_db(self):
        db_path = self.downloader.db_path

        if not self.database_settings_service.database_exists(db_path):
            messagebox.showwarning(
                self.translate("Warning"),
                self.translate("Database not found.")
            )
            return

        export_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite DB", "*.db")],
            title=self.translate("Export Database")
        )

        if not export_path:
            return

        try:
            self.database_settings_service.export_database(db_path, export_path)
            messagebox.showinfo(
                self.translate("Success"),
                self.translate("The database was exported successfully.")
            )
        except Exception as e:
            messagebox.showerror(
                self.translate("Error"),
                self.translate(f"Error exporting database: {e}")
            )

    def clear_db(self):
        confirm = messagebox.askyesno(self.translate("Confirm"), 
                                      self.translate("Are you sure you want to clear the database? This will delete all download records."))
        if confirm:
            try:
                self.downloader.clear_database()
                messagebox.showinfo(self.translate("Success"), self.translate("The database was cleared successfully."))
            except Exception as e:
                messagebox.showerror(self.translate("Error"), self.translate(f"Error clearing database: {e}"))

    def apply_download_settings(
        self,
        max_downloads_combobox,
        folder_structure_combobox,
        retry_combobox,
        retry_interval_entry,
        file_naming_combobox,
    ):
        try:
            parsed_values = self.download_settings_service.parse_form_values(
                max_downloads_value=max_downloads_combobox.get(),
                folder_structure_value=folder_structure_combobox.get(),
                max_retries_value=retry_combobox.get(),
                retry_interval_value=retry_interval_entry.get(),
                file_naming_mode_label=file_naming_combobox.get(),
            )

            self.settings = self.download_settings_service.apply_to_settings(
                self.settings,
                parsed_values
            )
            self.save_settings()
            self.download_settings_service.apply_to_downloader(self.downloader, parsed_values)

            messagebox.showinfo(
                self.translate("Éxito"),
                self.translate("La configuración de descargas se aplicó correctamente.")
            )

        except ValueError:
            messagebox.showerror(
                self.translate("Error"),
                self.translate("Por favor, ingresa valores numéricos válidos.")
            )
            
    def apply_language_settings(self, selected_language_name):
        success, message = self.settings_service.apply_language_settings(
            settings=self.settings,
            selected_language_name=selected_language_name,
            languages=self.languages,
            save_language_preference_func=self.save_language_preference,
            load_translations_func=self.load_translations,
            update_ui_texts_func=self.update_ui_texts,
        )

        if success:
            messagebox.showinfo(self.translate("Success"), self.translate(message))
        else:
            messagebox.showwarning(self.translate("Warning"), self.translate(message))

    def update_treeview(self):
        """Update the TreeViews to display the folder structure."""
        if hasattr(self, 'default_treeview') and hasattr(self, 'post_treeview'):
            self.default_treeview.delete(*self.default_treeview.get_children())
            self.post_treeview.delete(*self.post_treeview.get_children())

            root = self.default_treeview.insert("", "end", text="User", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="images", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="videos", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="documents", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.insert(root, "end", text="compressed", image=self.folder_structure_icons.get('folder'))
            self.default_treeview.item(root, open=True)

            post_root = self.post_treeview.insert("", "end", text="User", image=self.folder_structure_icons.get('folder'))
            post = self.post_treeview.insert(post_root, "end", text="post_id", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="images", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="videos", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="documents", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.insert(post, "end", text="compressed", image=self.folder_structure_icons.get('folder'))
            self.post_treeview.item(post_root, open=True)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def get_language_name(self, lang_code):
        return self.settings_service.get_language_name(self.languages, lang_code)

    def change_theme_in_thread(self, theme_name):
        def on_done(result):
            success, message = result
            if success:
                self.parent.after(
                    0,
                    lambda: messagebox.showinfo(self.translate("Success"), self.translate(message))
                )

        self.settings_service.change_theme_in_thread(self.settings, theme_name, callback=on_done)

    def apply_theme(self, theme_name):
        success, message = self.settings_service.apply_theme(self.settings, theme_name)
        if success:
            messagebox.showinfo(self.translate("Success"), self.translate(message))

    def center_window(self, window, width, height):
        self.settings_service.center_window(window, width, height)
