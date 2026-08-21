"""First-run and application-data setup."""

from __future__ import annotations

import json
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtWidgets import QFileDialog, QDialog
from PySide6.QtUiTools import QUiLoader

from ui.theme import DEFAULT_SETTINGS


@dataclass(frozen=True)
class StartupContext:
    data_dir: Path
    settings_path: Path
    database_path: Path
    portable: bool


def default_pictures_dir() -> Path:
    """Return the user's platform picture directory when discoverable."""
    if platform.system() in {"Windows", "Darwin"}:
        return Path.home() / "Pictures"
    xdg_config = Path.home() / ".config" / "user-dirs.dirs"
    if xdg_config.exists():
        for line in xdg_config.read_text(encoding="utf-8").splitlines():
            if line.startswith("XDG_PICTURES_DIR="):
                value = line.split("=", 1)[1].strip().strip('"')
                return Path(value.replace("$HOME", str(Path.home())))
    return Path.home() / "Pictures"


def default_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        root = os.environ.get("APPDATA")
        return Path(root) / "Drakindex" if root else Path.home() / "AppData/Roaming/Drakindex"
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Drakindex"
    root = os.environ.get("XDG_CONFIG_HOME")
    return (Path(root) if root else Path.home() / ".config") / "drakindex"


def _write_defaults(settings_path: Path) -> None:
    settings = {**DEFAULT_SETTINGS, "scan_folders": [str(default_pictures_dir())]}
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def _dialog():
    ui_path = Path(__file__).resolve().parent / "ui" / "initialstart.ui"
    ui_file = QFile(str(ui_path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Could not open {ui_path}")
    dialog = QUiLoader().load(ui_file, None)
    ui_file.close()
    if dialog is None:
        raise RuntimeError("Could not load the first-launch dialog")
    dialog.setWindowTitle("Welcome to Drakindex")
    dialog.title.setText("Welcome to Drakindex!")
    descriptions = [
        "Create a new configuration in the normal user data directory.",
        "Import settings and a database from a folder you choose.",
        "Keep application data beside this application for external-drive use.",
        "Use an external-drive data directory while importing existing data.",
    ]
    dialog.pickdesc.setText(descriptions[0])
    dialog.pick.currentIndexChanged.connect(lambda i: dialog.pickdesc.setText(descriptions[i]))
    dialog.pushButton.setDefault(True)
    dialog.pushButton.clicked.connect(dialog.accept)
    return dialog


def ensure_initialized(app, project_dir: str | os.PathLike[str] | None = None) -> StartupContext:
    """Ensure startup files exist and return paths used by the application."""
    project = Path(project_dir or Path(__file__).resolve().parent)
    # The database is the installation marker.  A database without settings
    # is never silently repaired: settings.json is required for a valid
    # existing installation and must be restored by the user/import flow.
    database_path = project / "database.db"
    settings_path = project / "settings.json"
    if database_path.exists():
        if not settings_path.exists():
            raise RuntimeError(
                f"Critical startup failure: {settings_path} is missing while {database_path} exists."
            )
        return StartupContext(project, settings_path, database_path, (project / "portable.flag").exists())

    dialog = _dialog()
    if dialog.exec() != QDialog.Accepted:
        raise SystemExit("First-launch setup was cancelled.")
    mode = dialog.pick.currentIndex()
    portable = mode in {2, 3}
    # Both normal and portable installations keep their application data in
    # the primary application folder.  Portable mode is recorded explicitly
    # so it can be distinguished later without relocating the database.
    target = project
    source = None
    if mode in {1, 3}:
        selected = QFileDialog.getExistingDirectory(dialog, "Choose existing Drakindex data")
        if not selected:
            raise SystemExit("No configuration folder was selected.")
        source = Path(selected)
    target.mkdir(parents=True, exist_ok=True)
    if source is not None:
        source_settings = source / "settings.json"
        if not source_settings.exists():
            raise RuntimeError("The selected folder does not contain settings.json")
        shutil.copy2(source_settings, target / "settings.json")
        source_db = source / "database.db"
        if source_db.exists():
            shutil.copy2(source_db, target / "database.db")
        else:
            raise RuntimeError("The selected folder does not contain database.db")
    elif not (target / "settings.json").exists():
        _write_defaults(target / "settings.json")
    if portable:
        (target / "portable.flag").touch()
    return StartupContext(target, target / "settings.json", target / "database.db", portable)
