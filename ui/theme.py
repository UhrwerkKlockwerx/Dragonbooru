"""Settings loading and application-wide Qt stylesheet support."""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SET_FILE = BASE_DIR / "settings.json"
THEME_FILE = BASE_DIR / "themes.json"


FALLBACK_THEME = {
    "background": "#181a33",
    "surface": "#21244e",
    "surface_hover": "#3c7083",
    "accent": "#141662",
    "accent_hover": "#3c7083",
    "selection": "#7f9aff",
    "text": "#7fc3ff",
    "text_selected": "#181a33",
    "text_muted": "#7f9aff",
    "text_muted_selected": "#45548c",
    "text_disabled": "#7f9aff",
    "border": "#141662"
}

DEFAULT_SETTINGS = {
    "images_per_page": 20,
    "safe_mode": False,
    "blacklisted_tags": [],
    "theme": "Deep Blue",
}

REQUIRED_THEME_KEYS = frozenset(FALLBACK_THEME)


def load_settings(path=None):
    settings_file = Path(path) if path is not None else SET_FILE
    try:
        with open(settings_file, "r", encoding="utf-8") as file:
            settings = json.load(file)

    except FileNotFoundError:
        raise RuntimeError(
            f'CRITICAL: "{settings_file}" could not be found.'
        )

    except json.JSONDecodeError:
        raise RuntimeError(
            f'CRITICAL: "{settings_file}" contains invalid JSON.'
        )

    if not isinstance(settings, dict):
        raise RuntimeError(
            f'CRITICAL: "{settings_file}" must contain a JSON object.'
        )

    # Keep older or partially edited settings files usable while adding new
    # settings in future versions.
    return {**DEFAULT_SETTINGS, **settings}


def save_settings(settings, path=None):
    """Persist settings atomically, creating the parent directory."""
    settings_file = Path(path) if path is not None else SET_FILE
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = settings_file.with_suffix(settings_file.suffix + ".tmp")
    temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    temporary.replace(settings_file)


def available_themes():
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as file:
            themes = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return ["Deep Blue"]
    return list(themes) if isinstance(themes, dict) else ["Deep Blue"]


def load_theme(theme_name):
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as file:
            themes = json.load(file)

    except FileNotFoundError:
        print(
            'WARNING: "themes.json" could not be found. '
            'Using fallback theme.'
        )
        return FALLBACK_THEME

    except json.JSONDecodeError:
        print(
            'WARNING: "themes.json" contains invalid JSON. '
            'Using fallback theme.'
        )
        return FALLBACK_THEME

    if not isinstance(themes, dict) or theme_name not in themes:
        print(
            f'WARNING: Theme "{theme_name}" was not found. '
            'Using fallback theme.'
        )
        return FALLBACK_THEME

    theme = themes[theme_name]
    if not isinstance(theme, dict) or not REQUIRED_THEME_KEYS.issubset(theme):
        print(
            f'WARNING: Theme "{theme_name}" is incomplete. '
            'Using fallback theme.'
        )
        return FALLBACK_THEME

    return theme


def build_stylesheet(theme):
    return f"""
    QWidget {{
        background-color: {theme["background"]};
        color: {theme["text"]};
    }}

    QMainWindow {{
        background-color: {theme["background"]};
    }}

    QFrame#bottomBar, QFrame#searchToolbar {{
        background-color: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 5px;
    }}

    QGroupBox {{
        background-color: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 5px;
        margin-top: 12px;
        padding: 12px;
        font-weight: bold;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
        color: {theme["text"]};
    }}

    QPushButton {{
        background-color: {theme["surface"]};
        color: {theme["text"]};
        border: 1px solid {theme["border"]};
        border-radius: 5px;
        padding: 7px 14px;
    }}

    QPushButton:hover {{
        background-color: {theme["surface_hover"]};
        color: {theme["text"]};
    }}

    QPushButton:pressed {{
        background-color: {theme["accent"]};
        color: {theme["text_selected"]};
    }}

    QPushButton:disabled {{
        background-color: {theme["surface"]};
        color: {theme["text_disabled"]};
    }}

    /* Primary actions use the palette accent; ordinary controls use surface. */
    QPushButton#search,
    QPushButton#settings,
    QPushButton#saveButton,
    QPushButton#apply,
    QPushButton#addFolderButton,
    QPushButton#rescanButton {{
        background-color: {theme["accent"]};
        color: {theme["text"]};
        border-color: {theme["accent"]};
    }}

    QPushButton#search:hover,
    QPushButton#settings:hover,
    QPushButton#saveButton:hover,
    QPushButton#apply:hover,
    QPushButton#addFolderButton:hover,
    QPushButton#rescanButton:hover {{
        background-color: {theme["accent_hover"]};
        border-color: {theme["accent_hover"]};
    }}

    QPushButton#search:pressed,
    QPushButton#settings:pressed,
    QPushButton#saveButton:pressed,
    QPushButton#apply:pressed,
    QPushButton#addFolderButton:pressed,
    QPushButton#rescanButton:pressed {{
        background-color: {theme["selection"]};
        color: {theme["text_selected"]};
    }}

    QLineEdit, QSpinBox, QComboBox, QListWidget {{
        background-color: {theme["surface"]};
        color: {theme["text"]};
        border: 1px solid {theme["border"]};
        border-radius: 4px;
        padding: 5px;
    }}

    QLineEdit:hover, QSpinBox:hover, QComboBox:hover, QListWidget:hover {{
        background-color: {theme["surface_hover"]};
    }}

    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QListWidget:focus {{
        background-color: {theme["surface"]};
        border: 1px solid {theme["selection"]};
    }}

    QComboBox QAbstractItemView {{
        background-color: {theme["surface"]};
        color: {theme["text"]};
        selection-background-color: {theme["selection"]};
        selection-color: {theme["text_selected"]};
        border: 1px solid {theme["border"]};
    }}

    QListWidget::item:selected {{
        background-color: {theme["selection"]};
        color: {theme["text_selected"]};
    }}

    QListWidget::item:selected:!active {{
        background-color: {theme["surface_hover"]};
        color: {theme["text_muted_selected"]};
    }}

    QCheckBox {{
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        background-color: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 3px;
    }}

    QCheckBox::indicator:hover {{
        background-color: {theme["surface_hover"]};
    }}

    QCheckBox::indicator:checked {{
        background-color: {theme["accent"]};
        border-color: {theme["accent_hover"]};
    }}

    QScrollArea {{
        border: none;
    }}

    QScrollBar:vertical, QScrollBar:horizontal {{
        background-color: {theme["background"]};
        border: 1px solid {theme["border"]};
        margin: 0;
    }}

    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background-color: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 4px;
        min-height: 24px;
        min-width: 24px;
    }}

    QScrollBar::handle:hover {{
        background-color: {theme["surface_hover"]};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        background-color: {theme["accent"]};
        border: none;
    }}

    QLabel#blacklistHint,
    QLabel#themeHint,
    QLabel#libraryDescription,
    QLabel#settingsStatusLabel,
    QLabel#perPageLabel,
    QLabel#ver {{
        color: {theme["text_muted"]};
    }}

    QLabel {{
        background-color: transparent;
        color: {theme["text"]};
    }}

    QToolTip {{
        background-color: {theme["surface"]};
        color: {theme["text"]};
        border: 1px solid {theme["border"]};
    }}
    """


def apply_theme(app, theme_name):
    theme = load_theme(theme_name)
    stylesheet = build_stylesheet(theme)
    app.setStyleSheet(stylesheet)
