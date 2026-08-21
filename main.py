"""Application entry point.
Formerly Dragonbooru. This is the entry point for Drakindex, where
we call bootstrap scripts and start the app or setup.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui import theme
from ui import main_window
from db import Database

import firstlaunchhandler

if getattr(sys, "frozen", False):
    # In a packaged build, persistent application data belongs beside the
    # executable rather than inside PyInstaller's temporary/internal files.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

VERSION_FILE = BASE_DIR/"version.txt"

def main():
    version = VERSION_FILE.read_text(encoding='utf-8').strip()
    app = QApplication(sys.argv)
    startup = firstlaunchhandler.ensure_initialized(app, BASE_DIR)
    settings = theme.load_settings(startup.settings_path)
    theme.apply_theme(app, settings["theme"])
    database = Database(startup.database_path)
    window = main_window.MainWindow(
        settings, version, settings_path=startup.settings_path, database=database
    )
    window.show()

    exit_code = app.exec()
    database.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
