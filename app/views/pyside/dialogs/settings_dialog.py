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
        self.on_settings_changed = on_settings_changed

        self.CONFIG_PATH = "resources/config/settings.json"
        self.COOKIES_PATH = "resources/config/cookies/simpcity.json"

        self.languages = self._load_languages_map()

        self.settings_service = SettingsWindowService(
            config_path=self.CONFIG_PATH,
            on_settings_changed=on_settings_changed
        )
        self.download_settings_service = DownloadSettingsService()
        self.cookies_settings_service = CookiesSettingsService(self.COOKIES_PATH)
        self.database_settings_service = DatabaseSettingsService()
        self.settings = self.settings_service.load_settings()

        self.setWindowTitle(self.translate("SETTINGS_WINDOW_TITLE", version=self.version))
        self.resize(920, 680)

        self._build_ui()

    def _load_languages_map(self):
        available = self.parent_window.translation_service.get_available_languages()
        languages = {
            item["name"]: item["code"]
            for item in available
            if "name" in item and "code" in item
        }

        if not languages:
            languages = {
                "English": "en",
                "Español": "es",
            }

        return languages

    def _t(self, key, **kwargs):
        try:
            return self.translate(key, **kwargs)
        except TypeError:
            text = self.translate(key)
            if kwargs:
                try:
                    return text.format(**kwargs)
                except Exception:
                    return text
            return text

    def _build_ui(self):
        root = QVBoxLayout(self)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.general_tab = QWidget()
        self.downloads_tab = QWidget()
        self.cookies_tab = QWidget()
        self.database_tab = QWidget()

        self.tabs.addTab(self.general_tab, self.translate("SETTINGS_TAB_GENERAL"))
        self.tabs.addTab(self.downloads_tab, self.translate("SETTINGS_TAB_DOWNLOADS"))
        self.tabs.addTab(self.cookies_tab, self.translate("SETTINGS_TAB_COOKIES"))
        self.tabs.addTab(self.database_tab, self.translate("SETTINGS_TAB_DATABASE"))

        self._build_general_tab()
        self._build_downloads_tab()
        self._build_cookies_tab()
        self._build_database_tab()

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)

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
        layout.addRow(QLabel(self.translate("SETTINGS_LANGUAGE")), self.language_combo)

        self.apply_language_button = QPushButton(self.translate("SETTINGS_APPLY_LANGUAGE"))
        self.apply_language_button.clicked.connect(self._apply_language)
        layout.addRow("", self.apply_language_button)

    def _build_downloads_tab(self):
        layout = QFormLayout(self.downloads_tab)

        self.max_downloads_combo = QComboBox()
        self.max_downloads_combo.addItems([str(i) for i in range(1, 33)])
        self.max_downloads_combo.setCurrentText(str(self.settings.get("max_downloads", 3)))
        layout.addRow(QLabel(self.translate("SETTINGS_MAX_DOWNLOADS")), self.max_downloads_combo)

        self.folder_structure_combo = QComboBox()
        self.folder_structure_combo.addItems(["default", "post_number"])
        self.folder_structure_combo.setCurrentText(self.settings.get("folder_structure", "default"))
        self.folder_structure_combo.currentTextChanged.connect(self.refresh_structure_preview)
        layout.addRow(QLabel(self.translate("SETTINGS_FOLDER_STRUCTURE")), self.folder_structure_combo)

        self.max_retries_combo = QComboBox()
        self.max_retries_combo.addItems([str(i) for i in range(0, 21)])
        self.max_retries_combo.setCurrentText(str(self.settings.get("max_retries", 3)))
        layout.addRow(QLabel(self.translate("SETTINGS_MAX_RETRIES")), self.max_retries_combo)

        self.retry_interval_edit = QLineEdit(str(self.settings.get("retry_interval", 2.0)))
        layout.addRow(QLabel(self.translate("SETTINGS_RETRY_INTERVAL_SECONDS")), self.retry_interval_edit)

        self.file_naming_combo = QComboBox()
        naming_options = self.download_settings_service.get_naming_options()
        self.file_naming_combo.addItems(naming_options)
        current_naming_label = self.download_settings_service.get_naming_label_from_setting(
            self.settings.get("file_naming_mode", 0)
        )
        self.file_naming_combo.setCurrentText(current_naming_label)
        self.file_naming_combo.currentTextChanged.connect(self.refresh_structure_preview)
        layout.addRow(QLabel(self.translate("SETTINGS_FILE_NAMING_MODE")), self.file_naming_combo)

        self.apply_downloads_button = QPushButton(self.translate("SETTINGS_APPLY_DOWNLOAD_SETTINGS"))
        self.apply_downloads_button.clicked.connect(self._apply_download_settings)
        layout.addRow("", self.apply_downloads_button)

    def _build_cookies_tab(self):
        layout = QVBoxLayout(self.cookies_tab)

        self.cookies_info_label = QLabel(self.translate("SETTINGS_COOKIES_INFO"))
        self.cookies_info_label.setWordWrap(True)

        self.cookies_tutorial_label = QLabel(self.translate("SETTINGS_COOKIES_TUTORIAL"))
        self.cookies_tutorial_label.setStyleSheet("color: #bfbfbf;")
        self.cookies_tutorial_label.setWordWrap(True)
        layout.addWidget(self.cookies_tutorial_label)

        layout.addWidget(self.cookies_info_label)

        self.cookies_text = QTextEdit()
        self.cookies_text.setPlainText(self.cookies_settings_service.load_cookies_text())
        layout.addWidget(self.cookies_text, 1)

        buttons_row = QHBoxLayout()

        self.import_cookies_button = QPushButton(self.translate("SETTINGS_IMPORT_COOKIES"))
        self.import_cookies_button.clicked.connect(self._import_cookies)
        buttons_row.addWidget(self.import_cookies_button)

        self.save_cookies_button = QPushButton(self.translate("SETTINGS_SAVE_COOKIES"))
        self.save_cookies_button.clicked.connect(self._save_cookies)
        buttons_row.addWidget(self.save_cookies_button)

        self.clear_cookies_button = QPushButton(self.translate("SETTINGS_CLEAR_COOKIES"))
        self.clear_cookies_button.clicked.connect(self._clear_cookies)
        buttons_row.addWidget(self.clear_cookies_button)

        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

    def _build_database_tab(self):
        layout = QVBoxLayout(self.database_tab)

        self.database_info_label = QLabel(self.translate("SETTINGS_DATABASE_INFO"))
        layout.addWidget(self.database_info_label)

        self.db_tree = QTreeWidget()
        self.db_tree.setColumnCount(5)
        self.db_tree.setHeaderLabels([
            self.translate("SETTINGS_DB_HEADER_ID"),
            self.translate("SETTINGS_DB_HEADER_FILE_NAME"),
            self.translate("SETTINGS_DB_HEADER_TYPE"),
            self.translate("SETTINGS_DB_HEADER_SIZE"),
            self.translate("SETTINGS_DB_HEADER_DOWNLOADED_AT"),
        ])
        self.db_tree.setSelectionMode(self.db_tree.SelectionMode.ExtendedSelection)
        layout.addWidget(self.db_tree, 1)

        buttons_row = QHBoxLayout()

        self.reload_db_button = QPushButton(self.translate("SETTINGS_RELOAD_DATABASE"))
        self.reload_db_button.clicked.connect(self.load_db_records)
        buttons_row.addWidget(self.reload_db_button)

        self.export_db_button = QPushButton(self.translate("SETTINGS_EXPORT_DATABASE"))
        self.export_db_button.clicked.connect(self._export_db)
        buttons_row.addWidget(self.export_db_button)

        self.delete_users_button = QPushButton(self.translate("SETTINGS_DELETE_SELECTED_USERS"))
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
    def _get_db_path(self):
        if self.downloader and hasattr(self.downloader, "db_path") and self.downloader.db_path:
            return self.downloader.db_path
        return "resources/config/downloads.db"

    def load_db_records(self):
        db_path = self._get_db_path()

        if not self.database_settings_service.database_exists(db_path):
            self.db_tree.clear()
            return

        try:
            rows = self.database_settings_service.fetch_download_rows(db_path)
            payload = self.database_settings_service.build_tree_payload(rows)
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self._t("SETTINGS_ERROR_LOADING_DATABASE", error=e)
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
                no_post_item = QTreeWidgetItem([self.translate("SETTINGS_NO_POST")])
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
        db_path = self._get_db_path()

        if not self.database_settings_service.database_exists(db_path):
            QMessageBox.warning(self, self.translate("WARNING"), self.translate("SETTINGS_DATABASE_FILE_DOES_NOT_EXIST"))
            return

        export_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translate("SETTINGS_EXPORT_DATABASE"),
            "",
            "SQLite DB (*.db)"
        )
        if not export_path:
            return

        try:
            self.database_settings_service.export_database(db_path, export_path)
            QMessageBox.information(
                self,
                self.translate("SUCCESS"),
                self.translate("SETTINGS_DATABASE_EXPORTED_SUCCESS")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self._t("SETTINGS_ERROR_EXPORTING_DATABASE", error=e)
            )

    def _delete_selected_users(self):
        db_path = self._get_db_path()
        if not self.database_settings_service.database_exists(db_path):
            QMessageBox.warning(self, self.translate("WARNING"), self.translate("SETTINGS_DATABASE_NOT_FOUND"))
            return

        selected_items = self.db_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                self.translate("WARNING"),
                self.translate("SETTINGS_SELECT_AT_LEAST_ONE_USER")
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
                self.translate("WARNING"),
                self.translate("SETTINGS_SELECT_VALID_USER_ENTRIES")
            )
            return

        confirm = QMessageBox.question(
            self,
            self.translate("CONFIRM"),
            self._t("SETTINGS_CONFIRM_DELETE_USERS", users=", ".join(user_ids))
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.database_settings_service.delete_users(db_path, user_ids)
            QMessageBox.information(
                self,
                self.translate("SUCCESS"),
                self.translate("SETTINGS_SELECTED_USERS_DELETED")
            )
            self.load_db_records()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self._t("SETTINGS_ERROR_DELETING_USERS", error=e)
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
            QMessageBox.information(self, self.translate("SUCCESS"), self.translate(message))
            self._retranslate_ui()
        else:
            QMessageBox.warning(self, self.translate("WARNING"), self.translate(message))

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
                self.translate("SUCCESS"),
                self.translate("SETTINGS_DOWNLOADS_APPLIED_SUCCESS")
            )

        except ValueError:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self.translate("SETTINGS_INVALID_NUMERIC_VALUES")
            )

    def _save_cookies(self):
        cookies_text = self.cookies_text.toPlainText().strip()
        try:
            self.cookies_settings_service.save_cookies_text(cookies_text)
            QMessageBox.information(
                self,
                self.translate("SUCCESS"),
                self.translate("SETTINGS_COOKIES_SAVED_SUCCESS")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self._t("SETTINGS_ERROR_SAVING_COOKIES", error=e)
            )

    def _import_cookies(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("SETTINGS_IMPORT_COOKIES"),
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
                self.translate("SUCCESS"),
                self.translate("SETTINGS_COOKIES_IMPORTED_SUCCESS")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self._t("SETTINGS_ERROR_IMPORTING_COOKIES", error=e)
            )

    def _clear_cookies(self):
        confirm = QMessageBox.question(
            self,
            self.translate("CONFIRM"),
            self.translate("SETTINGS_CONFIRM_CLEAR_COOKIES")
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.cookies_settings_service.clear_cookies()
            self.cookies_text.clear()
            QMessageBox.information(
                self,
                self.translate("SUCCESS"),
                self.translate("SETTINGS_COOKIES_CLEARED_SUCCESS")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.translate("ERROR"),
                self._t("SETTINGS_ERROR_CLEARING_COOKIES", error=e)
            )

    def _retranslate_ui(self):
        self.setWindowTitle(self._t("SETTINGS_WINDOW_TITLE", version=self.version))
        self.tabs.setTabText(0, self.translate("SETTINGS_TAB_GENERAL"))
        self.tabs.setTabText(1, self.translate("SETTINGS_TAB_DOWNLOADS"))
        self.tabs.setTabText(2, self.translate("SETTINGS_TAB_COOKIES"))
        self.tabs.setTabText(3, self.translate("SETTINGS_TAB_DATABASE"))
        self.apply_language_button.setText(self.translate("SETTINGS_APPLY_LANGUAGE"))
        self.apply_downloads_button.setText(self.translate("SETTINGS_APPLY_DOWNLOAD_SETTINGS"))
        self.cookies_info_label.setText(self.translate("SETTINGS_COOKIES_INFO"))
        self.cookies_tutorial_label.setText(self.translate("SETTINGS_COOKIES_TUTORIAL"))
        self.import_cookies_button.setText(self.translate("SETTINGS_IMPORT_COOKIES"))
        self.save_cookies_button.setText(self.translate("SETTINGS_SAVE_COOKIES"))
        self.clear_cookies_button.setText(self.translate("SETTINGS_CLEAR_COOKIES"))
        self.database_info_label.setText(self.translate("SETTINGS_DATABASE_INFO"))
        self.reload_db_button.setText(self.translate("SETTINGS_RELOAD_DATABASE"))
        self.export_db_button.setText(self.translate("SETTINGS_EXPORT_DATABASE"))
        self.delete_users_button.setText(self.translate("SETTINGS_DELETE_SELECTED_USERS"))
        self.db_tree.setHeaderLabels([
            self.translate("SETTINGS_DB_HEADER_ID"),
            self.translate("SETTINGS_DB_HEADER_FILE_NAME"),
            self.translate("SETTINGS_DB_HEADER_TYPE"),
            self.translate("SETTINGS_DB_HEADER_SIZE"),
            self.translate("SETTINGS_DB_HEADER_DOWNLOADED_AT"),
        ])