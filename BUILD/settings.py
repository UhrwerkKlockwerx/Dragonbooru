import os
import sys
import json

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- USER DATA DIR ---
APP_DIR = os.path.join(os.path.expanduser("~"), ".dragonbooru")
os.makedirs(APP_DIR, exist_ok=True)

# --- Writable files ---
delcache = os.path.join(APP_DIR, 'dcache.cache')
DB_FILE = os.path.join(APP_DIR, "tags.db")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

# --- User content ---
IMAGE_ROOT = os.path.join(APP_DIR, "images")
THUMB_ROOT = os.path.join(APP_DIR, "thumbnails")

os.makedirs(IMAGE_ROOT, exist_ok=True)
os.makedirs(THUMB_ROOT, exist_ok=True)

# --- Read-only bundled files ---
THEME_FILE = resource_path("themes.json")

marked_for_deletion = []

# Thumb and preview size configs. Soon this will be adjustable in settings.
THUMB_SIZE = (200, 200)  # thumbnail max size (px)
VIDEO_PREVIEW_SIZE = 720 # Video preview max size

# supported image extensions
SUPPORTED_EXT = (
".jpg",".jpeg",".png",".webp",".gif",".bmp",".tiff",".avif",".heic",".jp2",
".mp4",".webm",".mkv",".avi",".mov",".flv",".wmv",".m4v"
)
# supported video extensions
VIDEO_EXT = (".mp4",".webm",".mkv",".avi",".mov",".flv",".wmv",".m4v")
DEFAULT_SETTINGS = {
    "images_per_page": 60
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
            	return json.load(f)
        except:
            pass
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()

def save_settings(s):
    json.dump(s, open(SETTINGS_FILE, "w"), indent=2)
