import os
import shutil
import subprocess
import tkinter
from tkinter import messagebox
from db import *

def is_video(path):
    return path.lower().endswith(VIDEO_EXT)
    
# Video Support!!
def play_video(path):
    try:
        if shutil.which("vlc"):
            subprocess.Popen([
                "vlc",
                "--quiet",
                "--loop",
                "--one-instance",
                path
            ])
            return
        if shutil.which("flatpak"):
            try:
                subprocess.Popen([
                    "flatpak",
                    "run",
                    "org.videolan.VLC",
                    "--loop",
                    "--one-instance",
                    path
                ])
                return
            except Exception:
                pass
    except FileNotFoundError:
        print("VLC not found, trying ffplay")
    try:
        subprocess.Popen([
            "ffplay",
            "-loop", "0",
            path
        ])
        return
    except FileNotFoundError:
        messagebox.showerror(
            "Video Playback Error",
            "Neither VLC nor ffplay were found.\nInstall VLC or FFmpeg."
        )

