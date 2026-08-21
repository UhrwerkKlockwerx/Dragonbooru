"""Main-menu window loading and event handling."""

from pathlib import Path

from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QVBoxLayout

# Importing the generated module registers the Qt resource bundle before the
# Designer file is loaded. Do not remove this import just because it is unused.
from . import resources_rc
from . import theme

BASE_DIR = Path(__file__).resolve().parent.parent
UI_FILE = BASE_DIR/'ui'/'mainwindow.ui'

class MainWindow:
    """Load and control the application's main-menu Designer form."""

    def __init__(self, settings, version, settings_path=None, database=None):
        self.window = self.load_ui()
        self.settings = settings
        self.settings_path = settings_path
        self.database = database

        if 'b' in version:
            ver = f"{version} BETA - May Be Unstable"
        elif 'n' in version:
            ver = f"{version} NIGHTLY - May Be Unstable"
        elif 'd' in version:
            ver = f"{version} DEV BUILD, DO NOT DISTRIBUTE"
        else:
            ver = version
        self.version = ver

        # Designer stores the last selected stacked-widget page in the .ui
        # file.  Explicitly choose the menu at startup so a stale Designer
        # index can never open the application on a secondary screen.
        self.window.mainStack.setCurrentWidget(self.window.mainMenuPage)
        
        self.connect_signals()
        self.load_dynamic_content()

    def load_ui(self):
        loader = QUiLoader()
        ui_file = QFile(str(UI_FILE))

        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Could not open {UI_FILE}")

        window = loader.load(ui_file)
        ui_file.close()

        if window is None:
            raise RuntimeError('QT failed to open the UI file for the main menu screen.')

        return window

    def connect_signals(self):
        self.window.search.clicked.connect(self.search_clicked)
        self.window.settings.clicked.connect(self.settings_clicked)
        self.window.exit.clicked.connect(self.window.close)
        self.window.whatsnew.clicked.connect(self.whats_new_clicked)
        self.window.searchBackButton.clicked.connect(self.show_main_menu)
        self.window.settingsBackButton.clicked.connect(self.show_main_menu)
        self.window.imagesPerPageSpinBox.setValue(int(self.settings.get("images_per_page", 20)))
        self.window.safeModeCheckBox.setChecked(bool(self.settings.get("safe_mode", False)))
        self.window.blacklistEdit.setText(", ".join(self.settings.get("blacklisted_tags", [])))
        self.window.scanFoldersList.addItems(self.settings.get("scan_folders", []))
        self.window.rescanButton.setEnabled(self.window.scanFoldersList.count() > 0)
        self.window.themeComboBox.addItems(theme.available_themes())
        self.window.themeComboBox.setCurrentText(self.settings.get("theme", "Deep Blue"))
        self.window.addFolderButton.clicked.connect(self.add_folder)
        self.window.removeFolderButton.clicked.connect(self.remove_folder)
        self.window.scanFoldersList.itemSelectionChanged.connect(
            lambda: self.window.removeFolderButton.setEnabled(bool(self.window.scanFoldersList.selectedItems()))
        )
        self.window.rescanButton.clicked.connect(self.rescan_library)
        self.window.saveButton.clicked.connect(self.save_settings)
        self.window.themeComboBox.currentTextChanged.connect(self.preview_theme)

    def load_dynamic_content(self):
        self.window.ver.setText(f"Version '{self.version}'")

    def search_clicked(self):
        self.window.mainStack.setCurrentWidget(self.window.searchPage)

    def settings_clicked(self):
        self.window.mainStack.setCurrentWidget(self.window.settingsPage)

    def show_main_menu(self):
        """Return from a full-screen page to the application's menu."""
        self.window.mainStack.setCurrentWidget(self.window.mainMenuPage)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self.window, "Choose library folder")
        if folder and not self.window.scanFoldersList.findItems(
            folder, Qt.MatchFlag.MatchExactly
        ):
            self.window.scanFoldersList.addItem(folder)
            self.window.rescanButton.setEnabled(True)

    def remove_folder(self):
        for item in self.window.scanFoldersList.selectedItems():
            self.window.scanFoldersList.takeItem(self.window.scanFoldersList.row(item))
        self.window.rescanButton.setEnabled(self.window.scanFoldersList.count() > 0)

    def _settings_from_form(self):
        blacklist = [tag.strip() for tag in self.window.blacklistEdit.text().split(",") if tag.strip()]
        return {**self.settings,
            "images_per_page": self.window.imagesPerPageSpinBox.value(),
            "safe_mode": self.window.safeModeCheckBox.isChecked(),
            "blacklisted_tags": blacklist,
            "scan_folders": [self.window.scanFoldersList.item(i).text() for i in range(self.window.scanFoldersList.count())],
            "theme": self.window.themeComboBox.currentText(),
        }

    def save_settings(self):
        self.settings = self._settings_from_form()
        theme.save_settings(self.settings, self.settings_path)
        self.window.settingsStatusLabel.setText("Settings saved.")
        self.window.rescanButton.setEnabled(self.window.scanFoldersList.count() > 0)

    def preview_theme(self, name):
        theme.apply_theme(QApplication.instance(), name)

    def rescan_library(self):
        if self.database is None:
            self.window.settingsStatusLabel.setText("Database is not available.")
            return
        folders = [self.window.scanFoldersList.item(i).text() for i in range(self.window.scanFoldersList.count())]
        result = self.database.scan_folders(folders)
        self.window.settingsStatusLabel.setText(f"Indexed {result.inserted} new media files.")

    def whats_new_clicked(self):
        ui_path = BASE_DIR / "ui" / "whatsnew.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            return
        dialog = QUiLoader().load(ui_file, self.window)
        ui_file.close()
        if dialog is not None:
            label = QLabel("Review the changelog for recent updates.", dialog)
            label.setWordWrap(True)
            dialog.scrollAreaWidgetContents.setLayout(QVBoxLayout())
            dialog.scrollAreaWidgetContents.layout().addWidget(label)
            dialog.exec()

    def show(self):
        self.window.show()
