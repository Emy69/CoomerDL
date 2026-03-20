from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QTextEdit,
    QFileDialog,
)

from app.services.settings_window_service import SettingsWindowService
from app.services.download_settings_service import DownloadSettingsService
from app.services.structure_preview_service import StructurePreviewService
from app.services.cookies_settings_service import CookiesSettingsService
from app.services.database_settings_service import DatabaseSettingsService
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(
        self,
        parent,
        tr,
        load_translations,
        update_ui_texts,
        save_language_preference,
        version,
        downloader,
        check_for_new_version,
        on_settings_changed=None,
    ):
        super().__init__(parent)

        self.parent_window = parent
        self.translate = tr
        self.load_translations = load_translations
        self.update_ui_texts = update_ui_texts
        self.save_language_preference = save_language_preference
        self.version = version
        self.downloader = downloader
        self.check_for_new_version = check_for_new_version
        self.on_settings_changed = on_settings_changed

        self.CONFIG_PATH = "resources/config/settings.json"
        self.COOKIES_PATH = "resources/config/cookies.json"

        self.languages = {
            "English": "en",
            "Español": "es",
        }

        self.settings_service = SettingsWindowService(
            config_path=self.CONFIG_PATH,
            on_settings_changed=on_settings_changed
        )
        self.download_settings_service = DownloadSettingsService()
        self.structure_preview_service = StructurePreviewService()
        self.cookies_settings_service = CookiesSettingsService(self.COOKIES_PATH)
        self.database_settings_service = DatabaseSettingsService()
        self.settings = self.settings_service.load_settings()

        self.setWindowTitle(f"Settings [{self.version}]")
        self.resize(920, 680)

        self._build_ui()

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.general_tab = QWidget()
        self.downloads_tab = QWidget()
        self.structure_tab = QWidget()
        self.cookies_tab = QWidget()
        self.database_tab = QWidget()

        self.tabs.addTab(self.general_tab, self.translate("General"))
        self.tabs.addTab(self.downloads_tab, self.translate("Downloads"))
        self.tabs.addTab(self.structure_tab, self.translate("Structure"))
        self.tabs.addTab(self.cookies_tab, self.translate("Cookies"))
        self.tabs.addTab(self.database_tab, self.translate("Database"))

        self._build_general_tab()
        self._build_downloads_tab()
        self._build_structure_tab()
        self._build_cookies_tab()
        self._build_database_tab()

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)

        self.check_updates_button = QPushButton(self.translate("Check for Updates"))
        self.check_updates_button.clicked.connect(lambda: self.check_for_new_version(False))
        buttons_row.addWidget(self.check_updates_button)

        self.close_button = QPushButton(self.translate("Close"))
        self.close_button.clicked.connect(self.accept)
        buttons_row.addWidget(self.close_button)

        root.addLayout(buttons_row)

    def _build_general_tab(self):
        layout = QFormLayout(self.general_tab)

        self.language_combo = QComboBox()
        self.language_combo.addItems(list(self.languages.keys()))
        self.language_combo.setCurrentText(
            self.settings_service.get_language_name(
                self.languages,
                self.settings.get("language", "en")
            )
        )
        layout.addRow(QLabel(self.translate("Language")), self.language_combo)

        self.apply_language_button = QPushButton(self.translate("Apply Language"))
        self.apply_language_button.clicked.connect(self._apply_language)
        layout.addRow("", self.apply_language_button)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Dark", "Light"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "System"))
        layout.addRow(QLabel(self.translate("Theme")), self.theme_combo)

        self.apply_theme_button = QPushButton(self.translate("Apply Theme"))
        self.apply_theme_button.clicked.connect(self._apply_theme)
        layout.addRow("", self.apply_theme_button)

    def _build_downloads_tab(self):
        layout = QFormLayout(self.downloads_tab)

        self.max_downloads_combo = QComboBox()
        self.max_downloads_combo.addItems([str(i) for i in range(1, 33)])
        self.max_downloads_combo.setCurrentText(str(self.settings.get("max_downloads", 3)))
        layout.addRow(QLabel(self.translate("Max Downloads")), self.max_downloads_combo)

        self.folder_structure_combo = QComboBox()
        self.folder_structure_combo.addItems(["default", "post_number"])
        self.folder_structure_combo.setCurrentText(self.settings.get("folder_structure", "default"))
        self.folder_structure_combo.currentTextChanged.connect(self.refresh_structure_preview)
        layout.addRow(QLabel(self.translate("Folder Structure")), self.folder_structure_combo)

        self.max_retries_combo = QComboBox()
        self.max_retries_combo.addItems([str(i) for i in range(0, 21)])
        self.max_retries_combo.setCurrentText(str(self.settings.get("max_retries", 3)))
        layout.addRow(QLabel(self.translate("Max Retries")), self.max_retries_combo)

        self.retry_interval_edit = QLineEdit(str(self.settings.get("retry_interval", 2.0)))
        layout.addRow(QLabel(self.translate("Retry Interval (seconds)")), self.retry_interval_edit)

        self.file_naming_combo = QComboBox()
        naming_options = self.download_settings_service.get_naming_options()
        self.file_naming_combo.addItems(naming_options)
        current_naming_label = self.download_settings_service.get_naming_label_from_setting(
            self.settings.get("file_naming_mode", 0)
        )
        self.file_naming_combo.setCurrentText(current_naming_label)
        self.file_naming_combo.currentTextChanged.connect(self.refresh_structure_preview)
        layout.addRow(QLabel(self.translate("File Naming Mode")), self.file_naming_combo)

        self.apply_downloads_button = QPushButton(self.translate("Apply Download Settings"))
        self.apply_downloads_button.clicked.connect(self._apply_download_settings)
        layout.addRow("", self.apply_downloads_button)

    def _build_structure_tab(self):
        layout = QVBoxLayout(self.structure_tab)

        self.structure_info_label = QLabel(
            self.translate("Preview of how files will be organized on disk.")
        )
        layout.addWidget(self.structure_info_label)

        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderHidden(True)
        layout.addWidget(self.structure_tree, 1)

        self.refresh_structure_preview()

    def _build_cookies_tab(self):
        layout = QVBoxLayout(self.cookies_tab)

        self.cookies_info_label = QLabel(
            self.translate("Here you can paste, import, save, or clear your cookies JSON.")
        )
        layout.addWidget(self.cookies_info_label)

        self.cookies_text = QTextEdit()
        self.cookies_text.setPlainText(self.cookies_settings_service.load_cookies_text())
        layout.addWidget(self.cookies_text, 1)

        buttons_row = QHBoxLayout()

        self.import_cookies_button = QPushButton(self.translate("Import Cookies"))
        self.import_cookies_button.clicked.connect(self._import_cookies)
        buttons_row.addWidget(self.import_cookies_button)

        self.save_cookies_button = QPushButton(self.translate("Save Cookies"))
        self.save_cookies_button.clicked.connect(self._save_cookies)
        buttons_row.addWidget(self.save_cookies_button)

        self.clear_cookies_button = QPushButton(self.translate("Clear Cookies"))
        self.clear_cookies_button.clicked.connect(self._clear_cookies)
        buttons_row.addWidget(self.clear_cookies_button)

        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

    def _build_database_tab(self):
        layout = QVBoxLayout(self.database_tab)

        self.database_info_label = QLabel(
            self.translate("Browse, export, and manage downloaded records from the database.")
        )
        layout.addWidget(self.database_info_label)

        self.db_tree = QTreeWidget()
        self.db_tree.setColumnCount(5)
        self.db_tree.setHeaderLabels([
            "ID", "File Name", "Type", "Size", "Downloaded At"
        ])
        self.db_tree.setSelectionMode(self.db_tree.SelectionMode.ExtendedSelection)
        layout.addWidget(self.db_tree, 1)

        buttons_row = QHBoxLayout()

        self.reload_db_button = QPushButton(self.translate("Reload Database"))
        self.reload_db_button.clicked.connect(self.load_db_records)
        buttons_row.addWidget(self.reload_db_button)

        self.export_db_button = QPushButton(self.translate("Export Database"))
        self.export_db_button.clicked.connect(self._export_db)
        buttons_row.addWidget(self.export_db_button)

        self.delete_users_button = QPushButton(self.translate("Delete Selected Users"))
        self.delete_users_button.clicked.connect(self._delete_selected_users)
        buttons_row.addWidget(self.delete_users_button)

        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        self.load_db_records()

    # ------------------------------------------------------------
    # Structure preview
    # ------------------------------------------------------------
    def build_structure_preview_payload(self):
        temp_settings = dict(self.settings)
        temp_settings["folder_structure"] = self.folder_structure_combo.currentText()
        temp_settings["file_naming_mode"] = (
            self.download_settings_service.NAMING_MODE_LABEL_TO_VALUE.get(
                self.file_naming_combo.currentText(),
                0
            )
        )
        return self.structure_preview_service.build_preview_payload(temp_settings)

    def refresh_structure_preview(self):
        if not hasattr(self, "structure_tree"):
            return

        payload = self.build_structure_preview_payload()
        self.structure_tree.clear()

        root_item = QTreeWidgetItem([payload["root"]])
        self.structure_tree.addTopLevelItem(root_item)
        self._populate_structure_nodes(root_item, payload)
        self.structure_tree.expandAll()

    def _populate_structure_nodes(self, parent_item, payload):
        for folder in payload.get("folders", []):
            folder_item = QTreeWidgetItem([folder["name"]])
            parent_item.addChild(folder_item)
            self._populate_structure_nodes(folder_item, folder)

        for file_name in payload.get("files", []):
            file_item = QTreeWidgetItem([file_name])
            parent_item.addChild(file_item)

    # ------------------------------------------------------------
    # Database
    # ------------------------------------------------------------
    def load_db_records(self):
        if not self.downloader or not hasattr(self.downloader, "db_path"):
            self.db_tree.clear()
            return

        db_path = self.downloader.db_path

        if not self.database_settings_service.database_exists(db_path):
            self.db_tree.clear()
            return

        try:
            rows = self.database_settings_service.fetch_download_rows(db_path)
            payload = self.database_settings_service.build_tree_payload(rows)
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate(f"Error loading database: {e}")
            )
            return

        self.db_tree.clear()

        for user_entry in payload:
            user_item = QTreeWidgetItem([user_entry["user"]])
            self.db_tree.addTopLevelItem(user_item)

            for post_id, items in user_entry["posts"].items():
                post_item = QTreeWidgetItem([post_id])
                user_item.addChild(post_item)

                for item in items:
                    file_item = QTreeWidgetItem([
                        str(item["id"]),
                        item["file_name"],
                        self.translate(item["file_type"]),
                        item["size_str"],
                        str(item["downloaded_at"]),
                    ])
                    post_item.addChild(file_item)

            if user_entry["no_post"]:
                no_post_item = QTreeWidgetItem([self.translate("No Post")])
                user_item.addChild(no_post_item)

                for item in user_entry["no_post"]:
                    file_item = QTreeWidgetItem([
                        str(item["id"]),
                        item["file_name"],
                        self.translate(item["file_type"]),
                        item["size_str"],
                        str(item["downloaded_at"]),
                    ])
                    no_post_item.addChild(file_item)

        self.db_tree.expandToDepth(0)

    def _export_db(self):
        if not self.downloader or not hasattr(self.downloader, "db_path"):
            QMessageBox.warning(self, self.translate("Warning"), self.translate("Database not found."))
            return

        db_path = self.downloader.db_path
        if not self.database_settings_service.database_exists(db_path):
            QMessageBox.warning(self, self.translate("Warning"), self.translate("Database not found."))
            return

        export_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translate("Export Database"),
            "",
            "SQLite DB (*.db)"
        )
        if not export_path:
            return

        try:
            self.database_settings_service.export_database(db_path, export_path)
            QMessageBox.information(
                self,
                self.translate("Success"),
                self.translate("The database was exported successfully.")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate(f"Error exporting database: {e}")
            )

    def _delete_selected_users(self):
        if not self.downloader or not hasattr(self.downloader, "db_path"):
            QMessageBox.warning(self, self.translate("Warning"), self.translate("Database not found."))
            return

        selected_items = self.db_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                self.translate("Warning"),
                self.translate("Please select at least one user to delete.")
            )
            return

        user_ids = []
        for item in selected_items:
            parent = item.parent()
            if parent is None:
                user_ids.append(item.text(0))

        user_ids = list(dict.fromkeys(user_ids))
        if not user_ids:
            QMessageBox.warning(
                self,
                self.translate("Warning"),
                self.translate("Please select valid user entries (not posts/files).")
            )
            return

        confirm = QMessageBox.question(
            self,
            self.translate("Confirm"),
            self.translate(
                "Are you sure you want to delete all records for user(s): {}?".format(
                    ", ".join(user_ids)
                )
            )
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.database_settings_service.delete_users(self.downloader.db_path, user_ids)
            QMessageBox.information(
                self,
                self.translate("Success"),
                self.translate("Selected user(s) and their records were deleted.")
            )
            self.load_db_records()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate(f"Error deleting user(s): {e}")
            )

    # ------------------------------------------------------------
    # actions
    # ------------------------------------------------------------
    def _apply_language(self):
        success, message = self.settings_service.apply_language_settings(
            settings=self.settings,
            selected_language_name=self.language_combo.currentText(),
            languages=self.languages,
            save_language_preference_func=self.save_language_preference,
            load_translations_func=self.load_translations,
            update_ui_texts_func=self.update_ui_texts,
        )

        if success:
            QMessageBox.information(self, self.translate("Success"), self.translate(message))
            self._retranslate_ui()
        else:
            QMessageBox.warning(self, self.translate("Warning"), self.translate(message))

    def _apply_theme(self):
        success, message = self.settings_service.apply_theme(
            self.settings,
            self.theme_combo.currentText()
        )
        if success:
            QMessageBox.information(self, self.translate("Success"), self.translate(message))

    def _apply_download_settings(self):
        try:
            parsed_values = self.download_settings_service.parse_form_values(
                max_downloads_value=self.max_downloads_combo.currentText(),
                folder_structure_value=self.folder_structure_combo.currentText(),
                max_retries_value=self.max_retries_combo.currentText(),
                retry_interval_value=self.retry_interval_edit.text(),
                file_naming_mode_label=self.file_naming_combo.currentText(),
            )

            self.settings = self.download_settings_service.apply_to_settings(
                self.settings,
                parsed_values
            )
            self.settings_service.save_settings(self.settings)
            self.download_settings_service.apply_to_downloader(self.downloader, parsed_values)

            if self.parent_window is not None:
                if hasattr(self.parent_window, "settings"):
                    self.parent_window.settings = self.settings
                if hasattr(self.parent_window, "max_downloads"):
                    self.parent_window.max_downloads = parsed_values["max_downloads"]

            self.refresh_structure_preview()

            QMessageBox.information(
                self,
                self.translate("Success"),
                self.translate("La configuración de descargas se aplicó correctamente.")
            )

        except ValueError:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate("Por favor, ingresa valores numéricos válidos.")
            )

    def _save_cookies(self):
        cookies_text = self.cookies_text.toPlainText().strip()
        try:
            self.cookies_settings_service.save_cookies_text(cookies_text)
            QMessageBox.information(
                self,
                self.translate("Success"),
                self.translate("Cookies were saved successfully.")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate(f"Error saving cookies: {e}")
            )

    def _import_cookies(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("Import Cookies"),
            "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return

        try:
            content = self.cookies_settings_service.import_cookies_file(file_path)
            self.cookies_text.setPlainText(content)
            QMessageBox.information(
                self,
                self.translate("Success"),
                self.translate("Cookies were imported successfully.")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate(f"Error importing cookies: {e}")
            )

    def _clear_cookies(self):
        confirm = QMessageBox.question(
            self,
            self.translate("Confirm"),
            self.translate("Are you sure you want to clear the saved cookies?")
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.cookies_settings_service.clear_cookies()
            self.cookies_text.clear()
            QMessageBox.information(
                self,
                self.translate("Success"),
                self.translate("Cookies were cleared successfully.")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("Error"),
                self.translate(f"Error clearing cookies: {e}")
            )

    def _retranslate_ui(self):
        self.setWindowTitle(f"Settings [{self.version}]")
        self.tabs.setTabText(0, self.translate("General"))
        self.tabs.setTabText(1, self.translate("Downloads"))
        self.tabs.setTabText(2, self.translate("Structure"))
        self.tabs.setTabText(3, self.translate("Cookies"))
        self.tabs.setTabText(4, self.translate("Database"))
        self.check_updates_button.setText(self.translate("Check for Updates"))
        self.close_button.setText(self.translate("Close"))
        self.apply_language_button.setText(self.translate("Apply Language"))
        self.apply_theme_button.setText(self.translate("Apply Theme"))
        self.apply_downloads_button.setText(self.translate("Apply Download Settings"))
        self.structure_info_label.setText(
            self.translate("Preview of how files will be organized on disk.")
        )
        self.cookies_info_label.setText(
            self.translate("Here you can paste, import, save, or clear your cookies JSON.")
        )
        self.import_cookies_button.setText(self.translate("Import Cookies"))
        self.save_cookies_button.setText(self.translate("Save Cookies"))
        self.clear_cookies_button.setText(self.translate("Clear Cookies"))
        self.database_info_label.setText(
            self.translate("Browse, export, and manage downloaded records from the database.")
        )
        self.reload_db_button.setText(self.translate("Reload Database"))
        self.export_db_button.setText(self.translate("Export Database"))
        self.delete_users_button.setText(self.translate("Delete Selected Users"))