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
)

from app.services.settings_window_service import SettingsWindowService
from app.services.download_settings_service import DownloadSettingsService


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

        self.languages = {
            "English": "en",
            "Español": "es",
        }

        self.settings_service = SettingsWindowService(
            config_path=self.CONFIG_PATH,
            on_settings_changed=on_settings_changed
        )
        self.download_settings_service = DownloadSettingsService()
        self.settings = self.settings_service.load_settings()

        self.setWindowTitle(f"Settings [{self.version}]")
        self.resize(700, 500)

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

        self.tabs.addTab(self.general_tab, self.translate("General"))
        self.tabs.addTab(self.downloads_tab, self.translate("Downloads"))

        self._build_general_tab()
        self._build_downloads_tab()

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
        layout.addRow(QLabel(self.translate("File Naming Mode")), self.file_naming_combo)

        self.apply_downloads_button = QPushButton(self.translate("Apply Download Settings"))
        self.apply_downloads_button.clicked.connect(self._apply_download_settings)
        layout.addRow("", self.apply_downloads_button)

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

            # aplicar también al runtime del parent si existe
            if self.parent_window is not None:
                if hasattr(self.parent_window, "settings"):
                    self.parent_window.settings = self.settings
                if hasattr(self.parent_window, "max_downloads"):
                    self.parent_window.max_downloads = parsed_values["max_downloads"]

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

    def _retranslate_ui(self):
        self.setWindowTitle(f"Settings [{self.version}]")
        self.tabs.setTabText(0, self.translate("General"))
        self.tabs.setTabText(1, self.translate("Downloads"))
        self.check_updates_button.setText(self.translate("Check for Updates"))
        self.close_button.setText(self.translate("Close"))
        self.apply_language_button.setText(self.translate("Apply Language"))
        self.apply_theme_button.setText(self.translate("Apply Theme"))
        self.apply_downloads_button.setText(self.translate("Apply Download Settings"))