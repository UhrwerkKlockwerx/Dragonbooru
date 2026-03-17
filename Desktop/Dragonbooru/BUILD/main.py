#!/usr/bin/env python3

"""
Dragonbooru - simple local tagger/browser (hahahahahaha "simple")

TODO:
✓ Make a proper contained grid for the results to collect in that has independent scroll.
✓ Make it so that if big image be big on image viewer, it have scrolly polly bar.
✓ Add configurable "safe mode" that automatically hides certain specified tags.
✓ Add video support via integration with VLC. iframes??? (if compatible)
✓ Add animated image support.
✓ Fix the UI to have PROPER screens instead of reusing the tag editor screen as an image viewer!
✓ Make it pretty (which means just copying e621 but making it ''''''legally distinct'''''' lmao
~ Batch Tagging (partially complete, just needs proper batch edit instead of just adding)
O Add pools for image pools
O Add loading icon

Possibly:
- Add a Sort By function
- Add custom themes thru css
- Private webapp? (security issues are a concern tho)
- Use Tab to complete a tag suggestion

Main Brand Colourway:
Background: #181a33
Background Highlights: #21244e
Selected: #3c7083
Accent: #141662
Text Primary: #7fc3ff
Text Primary Selected: #1a4852
Text Secondary: #7f9aff
Text Secondary Selected: #45548c
"""

ver = '1.0.5b'
version = f'Version: {ver}'

print("""
 (                                                              
 )\ )                                   )                       
(()/(   (       )  (  (              ( /(            (      (   
 /(_))  )(   ( /(  )\))(  (    (     )\())  (    (   )(    ))\  
(_))_  (()\  )(_))((_))\  )\   )\ ) ((_)\   )\   )\ (()\  /((_) 
 |   \  ((_)((_)_  (()(_)((_) _(_/( | |(_) ((_) ((_) ((_)(_))(  
 | |) || '_|/ _` |/ _` |/ _ \| ' \))| '_ \/ _ \/ _ \| '_|| || | 
 |___/ |_|  \__,_|\__, |\___/|_||_| |_.__/\___/\___/|_|   \_,_| 
                  |___/                                             

""")
print(version, "!!!")

import os
import theme
import shutil
import sqlite3
import platform
import tempfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from settings import *
from db import *
from autocomplete_entry import *
from video import *
from theme import *
from settings import resource_path

temp_files = []

def open_file_location(path):
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", path])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", path])
        else:
             # Try file managers that support highlighting
            try:
                subprocess.run(["nautilus", "--select", path])
            except FileNotFoundError:
                try:
                    subprocess.run(["dolphin", "--select", path])
                except FileNotFoundError:
                    try:
                        subprocess.run(["nemo", "--no-desktop", "--browser", path])
                    except FileNotFoundError:
                        # fallback: just open folder
                        subprocess.run(["xdg-open", os.path.dirname(path)])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file location.\n{e}")

settings = load_settings()
load_themes(settings)

os.makedirs(IMAGE_ROOT, exist_ok=True)
os.makedirs(THUMB_ROOT, exist_ok=True)
# os.makedirs(LIB_ROOT, exist_ok=True)

def thumbnail_path(img_path):
    # mirror directory structure under THUMB_ROOT and keep .jpg thumbnails
    rel = os.path.relpath(img_path, IMAGE_ROOT)
    base = os.path.splitext(rel)[0] + ".jpg"
    return os.path.join(THUMB_ROOT, base)

def ensure_thumbnail(img_path):
    dst = thumbnail_path(img_path)
    dst_dir = os.path.dirname(dst)
    os.makedirs(dst_dir, exist_ok=True)

    if is_video(img_path):
        try:
            if not os.path.exists(dst) or os.path.getmtime(img_path) > os.path.getmtime(dst):
                print("DEBUG: Attempting to create thumbnail for video: ", img_path)
                result = subprocess.run([
                    "ffmpeg",
                    "-y",
                    "-i", img_path,
                    "-vf", f"thumbnail,scale={THUMB_SIZE[0]}:{THUMB_SIZE[1]}:force_original_aspect_ratio=decrease",
                    "-frames:v", "1",
                    dst
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    print("FFMPEG ERROR: ", result.stderr.decode())
                    return None
                if not os.path.exists(dst):
                    print("ERROR: FFMPEG ran but thumbnail failed to create. ", dst)
                    return None
            return dst

        except Exception as e:
            print("Video Thumbnail Failed: ", img_path, e)
            return None
    
    try:
        regen = True

        if os.path.exists(dst):
            try:
                with Image.open(dst) as t:
                    if t.size[0] <= THUMB_SIZE[0] and t.size[1] <= THUMB_SIZE[1]:
                        regen = os.path.getmtime(img_path) > os.path.getmtime(dst)
            except:
                regen = True

        if regen:
            img = Image.open(img_path)
            print('"', img, '" does not have a thumbnail, or thumbnail invalid. Attempting to create a thumbnail...')
            img.thumbnail(THUMB_SIZE)
            # convert to RGB for saving as JPEG
            img = img.convert("RGB")
            img.save(dst, "JPEG", quality=85)
    except Exception as e:
        # if thumbnail creation fails, remove possibly broken thumb
        try:
            if os.path.exists(dst):
                os.remove(dst)
        except:
            pass
        # log the failure and return None so caller knows
        print("Thumbnail failed:", img_path, e)
        return None
    return dst

scan_and_index_images()
conn.commit()

# ---------------------------
# Tkinter UI: frame switching
# ---------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        import datetime
        from datetime import datetime
        date = datetime.now()
        if date.month == 6:
            self.icon = tk.PhotoImage(file=resource_path("icon_small_pride.png"))
        else:
            self.icon = tk.PhotoImage(file=resource_path("icon_small.png"))

        self.iconphoto(True, self.icon)
        
        apply_ttk_theme(self)
        self.title("Dragonbooru - Local Tag Browser")
        self.geometry("1100x800")
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenuPage, SearchPage, TagEditorPage, SettingsPage, MediaViewerPage):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MainMenuPage")

    def on_close(self):
        # Save deletion list to the dcache
        if marked_for_deletion:
            with open(delcache, "w") as f:
                for path in marked_for_deletion:
                    f.write(path + "\n")
        self.destroy()

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()

# --------------------
# Main menu
# --------------------
class MainMenuPage(ThemedFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        import datetime
        from datetime import datetime
        date = datetime.now()
        if date.month == 6:
            self.logo = tk.PhotoImage(file=resource_path("icon_pride.png"))
        else:
            self.logo = tk.PhotoImage(file=resource_path("icon.png"))
        tk.Label(self, image=self.logo).pack(pady=(20,10))
        self.controller = controller
        tk.Label(self, text="Dragonbooru", font=("Helvetica", 50)).pack(pady=35)
        #tk.Label(self, text=version, font=("Emotion Engine", 10)).pack(pady=3)

        tk.Button(self, text="Search", width=30, command=self.goto_search_page).pack(pady=6)
        tk.Button(self, text="Settings", width=30, command=lambda: controller.show_frame("SettingsPage")).pack(pady=6)
        tk.Button(self, text="Exit", width=30, command=self.controller.on_close).pack(pady=6)

        bottomframe = tk.Frame(self)
        bottomframe.pack(side='bottom', fill='x', pady=3)
        
        tk.Button(bottomframe, text="What's New", width=15, command=self.whats_new).pack(pady=3, side="right")

        if 'b' in ver or 'n' in ver or 'd' in ver: #Checks if b (bets), n (nightly), or d (demo) are in the version code
            fontsize = 15
            if 'b' in ver:
                tk.Label(bottomframe, text=f"{version} BETA", font=("Helvetica",fontsize)).pack(side='left', pady=6)
            elif 'n' in ver:
                tk.Label(bottomframe, text=f"{version} Nightly - May be unstable!!", font=("Helvetica",fontsize)).pack(side='left', pady=6)
            elif 'd' in ver:
                tk.Label(bottomframe, text=f"{version} DEMO - MAY VARY FROM MAIN STABLE RELEASES AND DEMOS!", font=("Helvetica",fontsize)).pack(side='left',pady=6)
        else:
            tk.Label(self, text=f"{version} Stable", font=("Helvetica",fontsize)).pack(side='left', pady=6)
            

    def goto_search_page(self):
        # Go to search page and display all images. Used to be for the tag editor.
        sp = self.controller.frames["SearchPage"]
        sp.set_images_list(self._all_images())
        self.controller.show_frame("SearchPage")
        # automatically open first image in tag editor if desired
        # For now, open TagEditor only when clicking a thumbnail

    def whats_new(self):
        whatsnew = open(resource_path('changelog.clg'), 'r')
        messagebox.showinfo(f"What's New for {ver}",
                            f"Here is what's new for version {ver}:\n \n{whatsnew.read()}"
                        )

    def _all_images(self):
        cur.execute("SELECT path FROM images")
        return [r[0] for r in cur.fetchall()]

# --------------------
# Search page
# --------------------
class SearchPage(ThemedFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.images = []  # current image path list (results)
        self.photo_refs = []  # keep PhotoImage refs to avoid GC
        self.page = 0
        self.per_page = settings.get("images_per_page", 60)

        top = tk.Frame(self)
        top.pack(fill="x", padx=6, pady=6)

        left = tk.Frame(top)
        left.pack(side="left")

        right = tk.Frame(top)
        right.pack(side="right")

        tk.Button(left, text="Back", command=lambda: controller.show_frame("MainMenuPage")).pack(side="left")

        self.search_entry = AutocompleteEntry(left, width=80)
        self.search_entry.bind("<Return>", lambda e: self.do_search(), add="+")
        self.search_entry.pack(side="left", padx=6)

        tk.Button(left, text="Search", command=self.do_search).pack(side="left", padx=6)

        tk.Label(left, text="Per page:").pack(side="left", padx=(10,0))

        self.per_page_var = tk.IntVar(value=self.per_page)

        per_spin = tk.Spinbox(
            left,
            from_=6,
            to=500,
            increment=6,
            textvariable=self.per_page_var,
            width=6
        )
        per_spin.pack(side="left")

        tk.Button(left, text="Apply", command=self.apply_per_page).pack(side="left", padx=4)

        # Tag editor button moved to top-right
        tk.Button(
            right,
            text="Open Tag Editor",
            command=self.open_tag_editor_for_selected
        ).pack(side="right", padx=6)

        # canvas for thumbnails with scrollbar inside a container frame      
        grid_container = tk.Frame(self)
        grid_container.pack(fill="both", expand=True, padx=6, pady=6)
        
        self.canvas = tk.Canvas(grid_container)
        self.scrollbar = ttk.Scrollbar(grid_container, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_window = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # mousewheel scrolling only when hovering canvas
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # bottom pagination
        bottom = tk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=6)

        center = tk.Frame(bottom)
        center.pack(anchor="center")

        tk.Button(center, text="Prev", command=self.prev_page).pack(side="left", padx=6)

        self.page_label = tk.Label(center, text="Page 0 / 0")
        self.page_label.pack(side="left", padx=6)

        tk.Button(center, text="Next", command=self.next_page).pack(side="left", padx=6)
        
        # selected thumbnail index
        self.selected_index = None

        self.selected_indexes = set()
        # Batch Tag Button!
        tk.Button(top, text="Batch Add Tags", command=self.batch_add_prompt).pack(side="right", padx=6)

    def open_media(self, path):
        mv = self.controller.frames["MediaViewerPage"]
        mv.set_images_list(self.images, self.images.index(path))
        self.controller.show_frame("MediaViewerPage")

    def on_canvas_resize(self, event):
        # keep inner frame width synced
        self.canvas.itemconfig(self.canvas_window, width=event.width)

        # redraw thumbnails when width changes
        if hasattr(self, "_last_canvas_width"):
            if abs(event.width - self._last_canvas_width) > THUMB_SIZE[0]:
                self.show_page()

        self._last_canvas_width = event.width


    def on_mousewheel(self, event):
        # Windows / Mac
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


    def on_mousewheel_linux(self, event):
        # Linux scroll events
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")


    def _bind_mousewheel(self, event):
        # Windows / Mac
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Linux
        self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux)


    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def apply_per_page(self):
        self.per_page = max(1, int(self.per_page_var.get()))
        settings["images_per_page"] = self.per_page
        save_settings(settings)
        self.page = 0
        self.show_page()

    def set_images_list(self, image_list):
        self.images = image_list[:]
        self.page = 0
        self.show_page()

    def do_search(self):
        q = self.search_entry.get().strip()

        required, excluded = parse_search_query(q)

        if settings.get("safe_mode", False):
            excluded.extend(settings.get("blacklisted_tags", []))

        results = search_images(required, excluded)

        if not results:
            messagebox.showinfo(
                "Search",
                "No results found.\nAre your tags spelled and formatted correctly?"
            )
            return

        self.set_images_list(results)

    def clear_inner(self):
        for widget in self.inner.winfo_children():
            widget.destroy()
        self.photo_refs.clear()
        self.selected_index = None

    def thumb_click(self, event, path, index):
        if event.state & 0x0001:  # shift
            self.select_thumbnail(event, index)
        else:
            self.selected_indexes = {index}
            self.open_media(path)

    def show_page(self):
        self.clear_inner()
        total = len(self.images)
        per = self.per_page
        pages = (total + per - 1) // per if total else 0
        self.page = max(0, min(self.page, max(0, pages-1)))
        start = self.page * per
        end = min(total, start + per)
        display = self.images[start:end]

        PADDING = 12                                # Set padding for thumb spacing
        thumb_space = THUMB_SIZE[0] + PADDING
        canvas_width = self.canvas.winfo_width()

        if canvas_width <= 1:
            canvas_width = 1000  # fallback during first render

        cols = max(1, canvas_width // thumb_space)
        thumb_w = THUMB_SIZE[0]
        r = 0
        c = 0
        for idx, path in enumerate(display):

            try:
                thumbfile = ensure_thumbnail(path)
                if not thumbfile or not os.path.exists(thumbfile):
                    continue

                with Image.open(thumbfile) as thumb:
                    imgtk = ImageTk.PhotoImage(thumb.copy())

            except Exception as e:
                print("Thumb load error:", path, e)
                continue

            self.photo_refs.append(imgtk)

            frame = tk.Frame(self.inner)
            frame.grid(row=r, column=c, padx=6, pady=6)

            b = tk.Button(frame, image=imgtk)
            b.pack()
            b.bind("<Button-1>", lambda e, p=path, i=start+idx: self.thumb_click(e, p, i))

            lbl = tk.Label(frame, text=os.path.basename(path), wraplength=THUMB_SIZE[0])
            lbl.pack()

            c += 1
            if c >= cols:
                c = 0
                r += 1

        self.page_label.config(text=f"Page {self.page+1} / {pages if pages>0 else 1}")

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.show_page()

    def next_page(self):
        total = len(self.images)
        per = self.per_page
        pages = (total + per - 1) // per if total else 0
        if self.page < pages - 1:
            self.page += 1
            self.show_page()

    def open_tag_editor(self, image_path):
        te = self.controller.frames["TagEditorPage"]
        te.set_image(image_path)
        self.controller.show_frame("TagEditorPage")

    def open_tag_editor_for_selected(self):
        # fallback: open first in current page if none selected
        if not self.images:
            return
        start = self.page * self.per_page
        if start < len(self.images):
            self.open_tag_editor(self.images[start])

    def select_thumbnail(self, event, index):
        # Simple toggle system in the meantime
        if event.state & 0x0001: #Shift key
            self.selected_indexes.add(index)
        else:
            self.selected_indexes = {index}
        print("DEBUG: Selected Indexes: ", self.selected_indexes)

    def batch_add_prompt(self):
        if not self.selected_indexes:
            messagebox.showinfo("Batch Add", "No thumbnails selected")
            return

        popup = tk.Toplevel(self)
        popup.title("Batch Add Tags")

        tk.Label(popup, text="Enter Tags (Comma Separated):").pack(padx=6, pady=6)

        entry = tk.Entry(popup, width=50)
        entry.pack(padx=6, pady=6)

        def add_tags():
            tags = [t.strip() for t in entry.get().split(",") if t.strip()]

            for idx in self.selected_indexes:
                path = self.images[idx]
                for tag in tags:
                    add_tag_to_image(path, tag)
            completed = len(self.selected_indexes)
            self.selected_indexes.clear()

            popup.destroy()
            messagebox.showinfo(
                "Batch Add",
                f"Added {tags} to {completed} images" # the dirty nasty way of doing it but it fucking works dont @ me plz
            )

        tk.Button(popup, text="Batch Add", command=add_tags).pack(padx=6, pady=6)
        

# --------------------
# Media Viewer Page
# --------------------
class MediaViewerPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.images_list = []
        self.current_index = 0
        self.preview_imgtk = None

        # Main Frame
        top = tk.Frame(self)
        top.pack(fill="both", expand=True)

        # Make it scrollable so it does not cut off at the bottom
        self.canvas = tk.Canvas(top)
        self.scroll_y = ttk.Scrollbar(top, orient="vertical", command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.canvas_window = self.canvas.create_window((0,0), window=self.inner_frame, anchor="n")
        
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Configure>", self.on_resize)

        # Image/video labelling uwu owo
        self.media_label = tk.Label(self.inner_frame, anchor="center")
        self.media_label.pack(pady=12)

        # Tag list
        self.tags_frame = tk.Frame(self.inner_frame)
        self.tags_frame.pack(pady=6)

        # Bottom control bar (the thing to control foxes)
        bar = tk.Frame(self)
        bar.pack(fill="x", pady=8)

        left = tk.Frame(bar)
        center = tk.Frame(bar)
        right = tk.Frame(bar)

        left.pack(side="left", padx=10)
        center.pack(side="left", expand=True)
        right.pack(side="right", padx=10)
        
        # Buttonz for the control bar at the bottom
        tk.Button(right, text="Previous", command=self.prev_media).pack(side="left", padx=6)
        tk.Button(left, text="Back", command=lambda: controller.show_frame("SearchPage")).pack(side="left", padx=6)
        tk.Button(center, text="Edit Post", command=self.open_tag_editor).pack(side="left", padx=6)
        tk.Button(center, text="Open File Location", command=self.open_folder).pack(side="left",padx=6)
        tk.Button(right, text="Next", command=self.next_media).pack(side="left", padx=6)

    def on_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        if self.images_list:
            self.show_current()

    def open_folder(self):
        if not self.images_list:
            return
        path = self.images_list[self.current_index]
        open_file_location(path)

    def open_tag_editor(self):
        if not self.images_list:
            return
        path = self.images_list[self.current_index]
        te = self.controller.frames["TagEditorPage"]
        te.set_image(path)
        self.controller.show_frame("TagEditorPage")

    def on_mousewheel(self, event):
        # Windows / Mac
        self.canvas.yview_scroll(int(-event.delta / 60), "units")

    # Quick note, Linux and Windows both have different scrolling methods for tkinter. Thus, we need to
    # define and set the methods on a per case basis. Messy? Absofuckinglutely. Functional? You bet.

    def on_mousewheel_linux(self, event):
        # Linux scroll events
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")


    def _bind_mousewheel(self, event):
        # Windows / Mac
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Linux
        self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux)


    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def animate_gif(self):
        if not self.frames:
            return

        frame, delay = self.frames[self.frame_index]

        self.media_label.config(image=frame)
        self.media_label.image = frame

        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.after_id = self.after(delay, self.animate_gif)


    def play_gif(self, img):
        self.frames = []
        self.frame_index = 0

        try:
            for frame in range(img.n_frames):
                img.seek(frame)

                frame_img = img.copy().convert("RGBA")
                canvas_width = self.canvas.winfo_width()

                if canvas_width < 100:
                    canvas_width = 1000 # Initial rendering fallback
                w, h = img.size
                scale = min(canvas_width / w, 1.0)
                new_size = (int(w * scale), int(h * scale))
                frame_img = frame_img.resize(new_size, Image.LANCZOS)

                duration = img.info.get("duration", 60)

                if duration < 10:
                    duration *= 10

                duration = max(duration, 30)

                self.frames.append(
                    (ImageTk.PhotoImage(frame_img), duration)
                )

        except Exception as e:
            print("GIF decode error:", e)
            return

        if not self.frames:
            return

        self.animate_gif()

    def set_images_list(self, images, start_index=0):
        self.images_list = images
        self.current_index = start_index
        self.show_current()

    def show_current(self):
        self.media_label.unbind("<Button-1>")
        self.media_label.config(image="", text="")
        if hasattr(self, "after_id"):
            try:
                self.after_cancel(self.after_id)
            except:
                pass
        if not self.images_list:
            return
        path = self.images_list[self.current_index]
        # clear prev tags
        for w in self.tags_frame.winfo_children():
            w.destroy()

        # Display media
        if is_video(path):
            try:
                preview_tmp = os.path.join(
                    tempfile.gettempdir(),
                    "preview_" + str(abs(hash(path))) + ".jpg"
                )
                temp_files.append(preview_tmp)

                if not os.path.exists(preview_tmp):
                    subprocess.run([
                        "ffmpeg",
                        "-y",
                        "-i", path,
                        "-vf", f"thumbnail,scale={VIDEO_PREVIEW_SIZE}:{VIDEO_PREVIEW_SIZE}:force_original_aspect_ratio=decrease",
                        "-frames:v", "1",
                        preview_tmp
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if os.path.exists(preview_tmp):
                    img = Image.open(preview_tmp)

                    canvas_width = self.canvas.winfo_width()
                    if canvas_width < 100:
                        canvas_width = 1000

                    w, h = img.size
                    scale = min(canvas_width / w, 1.0)
                    new_size = (int(w * scale), int(h * scale))

                    img = img.resize(new_size, Image.NEAREST)

                    self.preview_imgtk = ImageTk.PhotoImage(img)
                    self.media_label.config(image=self.preview_imgtk)

                    
                    # clicking thumbnail plays video
                    self.media_label.bind(
                        "<Button-1>",
                        lambda e, p=path: play_video(p)
                    )

                else:
                    self.media_label.config(text="Video preview unavailable")
            except Exception as e:
                print("Video preview error: ", e)
                self.media_label.config(text="Video preview unavailable")
        else:
            try:
                img = Image.open(path)

                if getattr(img, "is_animated", False):
                    self.play_gif(img)
                else:
                    canvas_width = self.canvas.winfo_width()

                    if canvas_width < 100:
                        canvas_width = 1000 # Initial rendering fallback
                    w, h = img.size
                    scale = min(canvas_width / w, 1.0)
                    new_size = (int(w * scale), int(h * scale))
                    img = img.resize(new_size, Image.LANCZOS)
                    self.preview_imgtk = ImageTk.PhotoImage(img)
                    self.media_label.config(image=self.preview_imgtk)
            except Exception as e:
                self.media_label.config(text="Preview Unavaliable :(")
                print('PREVIEW ERROR!!! ', e)

        # Display tags
        tags = get_tags_for_image_path(path)
        max_cols = max(4, self.winfo_width() // 120)
        for i, t in enumerate(tags):
            btn = tk.Button(self.tags_frame, text=t, command=lambda tg=t: self.search_tag(tg))
            btn.grid(row=i // max_cols, column=i % max_cols, padx=3, pady=3, sticky="w")

    def search_tag(self, tag):
        sp = self.controller.frames["SearchPage"]
        sp.search_entry.delete(0, tk.END)
        sp.search_entry.insert(0, tag)
        sp.do_search()
        self.controller.show_frame("SearchPage")

    def prev_media(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current()

    def next_media(self):
        if self.current_index < len(self.images_list) -1:
            self.current_index += 1
            self.show_current()

# --------------------
# Tag Editor Page
# --------------------
class TagEditorPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.current_path = None
        self.preview_imgtk = None

        top = tk.Frame(self)
        top.pack(fill="x", padx=6, pady=6)
        tk.Button(top, text="Back", command=lambda: controller.show_frame("SearchPage")).pack(side="left")
        tk.Label(top, text="Tag Editor", font=("Helvetica", 14)).pack(side="left", padx=10)

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=6, pady=6)

        left = tk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, width=300)
        right.pack(side="right", fill="y")

        # image preview area
        self.preview_label = tk.Label(left)
        self.preview_label.pack(fill="both", expand=True)

        self.path_label = tk.Label(left, text="", anchor="w")
        self.path_label.pack(fill="x")

        # tag list + controls
        tk.Label(right, text="Tags for this image:").pack(anchor="w", pady=(6,0))
        self.tags_listbox = tk.Listbox(right, selectmode="single", width=40, height=20)
        self.tags_listbox.pack(padx=6, pady=6)

        tk.Label(right, text="Add tags (comma separated):").pack(anchor="w")
        self.add_entry = tk.Entry(right, width=40)
        self.add_entry.pack(padx=6)

        tk.Button(right, text="Add", command=self.on_add).pack(pady=4)
        tk.Button(right, text="Remove Selected", command=self.on_remove).pack(pady=4)
        tk.Button(right, text="Save & Back to Search", command=self.save_and_back).pack(pady=10)
        tk.Button(right, text="Mark for Deletion", fg="red", bg="#ffb9a8", command=self.mark_for_deletion).pack(pady=4)

    def animate_gif(self):
        if not self.frames:
            return

        frame, delay = self.frames[self.frame_index]

        self.preview_label.config(image=frame)
        self.preview_label.image = frame # ref

        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.after_id = self.after(delay, self.animate_gif)

    def play_gif(self, img):
        self.frames = []
        self.frame_index = 0

        try:
            for frame in range(img.n_frames):
                img.seek(frame)
                frame_img = img.copy().convert("RGBA")
                frame_img.thumbnail((900, 900))

                # Duration MUST be read AFTER seek()!
                duration = img.info.get("duration", 60)

                # Some gifs store centiseconds instead of ms.
                if duration < 10:
                    duration *= 10

                # Prevent ludicrous speed being achieved in gif form
                duration = max(duration, 30)

                self.frames.append(
                    (ImageTk.PhotoImage(frame_img), duration)
                )

                # print("DEBUG: FRAME DUR: ", duration) # <<Debugging only

        except Exception as e:
            print("GIF decode error:", e)
            return

        if not self.frames:
            return

        self.animate_gif()
    
    def mark_for_deletion(self):
        if self.current_path and self.current_path not in marked_for_deletion:
            marked_for_deletion.append(self.current_path)
            print('Marked for deletion:', self.current_path)
            # Show it in tag editor too
            self.path_label.config(text=f'{self.current_path} [MFD]')

    def set_image(self, path):
        self.frames = []
        self.current_path = path
        self.path_label.config(text=path)

        # Stop previous gif animation if applicable
        if hasattr(self, "after_id"):
            try:
                self.after_cancel(self.after_id)
            except:
                pass
        
        # load preview
        if is_video(path):
            thumb = ensure_thumbnail(path)

            if thumb and os.path.exists(thumb):
                img = Image.open(thumb)
                img.thumbnail((900,900))

                imgtk = ImageTk.PhotoImage(img)
                self.preview_imgtk = imgtk
                self.preview_label.config(image=imgtk)
            else:
                self.preview_label.config(text="Video preview unavaliable")

        else:
            img = Image.open(path)
            if getattr(img, "is_animated", False):
                self.play_gif(img)
            else:
                img.thumbnail((900, 900))
                imgtk = ImageTk.PhotoImage(img)
                self.preview_imgtk = imgtk
                self.preview_label.config(image=imgtk)

        # populate tags listbox
        self.refresh_tags_listbox()

    def refresh_tags_listbox(self):
        self.tags_listbox.delete(0, tk.END)
        if not self.current_path:
            return
        tags = get_tags_for_image_path(self.current_path)
        for t in tags:
            self.tags_listbox.insert(tk.END, t)

    def on_add(self):
        text = self.add_entry.get().strip()
        if not text:
            return
        parts = [p.strip() for p in text.split(",") if p.strip()]
        for p in parts:
            add_tag_to_image(self.current_path, p)
        self.add_entry.delete(0, tk.END)
        self.refresh_tags_listbox()

    def on_remove(self):
        sel = self.tags_listbox.curselection()
        if not sel:
            return
        tag = self.tags_listbox.get(sel[0])
        remove_tag_from_image(self.current_path, tag)
        self.refresh_tags_listbox()

    def save_and_back(self):
        conn.commit()
        # return to search page (refresh thumbnails if needed)
        sp = self.controller.frames["SearchPage"]
        sp.show_page()
        self.controller.show_frame("SearchPage")

# --------------------
# Settings page
# --------------------
class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Settings", font=("Helvetica", 16)).pack(pady=10)
        tk.Button(self, text="Back", command=lambda: controller.show_frame("MainMenuPage")).pack()

        frm = tk.Frame(self)
        frm.pack(pady=6)

        tk.Label(frm, text="Images per page:").grid(row=0, column=0, sticky="w")

        self.pp_var = tk.IntVar(value=settings.get("images_per_page", 60))

        tk.Spinbox(
            frm,
            from_=6,
            to=500,
            increment=6,
            textvariable=self.pp_var,
            width=8
        ).grid(row=0, column=1, padx=6)

        self.safe_var = tk.BooleanVar(value=settings.get("safe_mode", False))

        self.theme_var = tk.StringVar(value=settings.get("theme", "Deep Blue"))

        from theme import THEMELIST

        theme_dropdown = ttk.Combobox(
                frm,
                textvariable=self.theme_var,
                values=list(THEMELIST),
                state="readonly",
                width=18
        )

        theme_dropdown.grid(row=4, column=1, padx=6)
        tk.Label(frm, text="Theme:").grid(row=4, column=0, sticky="w")

        theme_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda e: self.change_theme(self.theme_var.get())
        )

        tk.Checkbutton(
            frm,
            text="Safe Mode",
            variable=self.safe_var
        ).grid(row=1, column=0, columnspan=2)

        tk.Label(frm, text="Blacklisted tags (comma separated):").grid(row=2, column=0, sticky="w")

        self.blacklist_var = tk.StringVar(
            value=", ".join(settings.get("blacklisted_tags", []))
        )

        tk.Entry(frm, textvariable=self.blacklist_var, width=40).grid(row=2, column=1, padx=6)

        tk.Button(frm, text="Save", command=self.save_settings).grid(row=3, column=0, columnspan=2, pady=6)

    def change_theme(self, name):
        theme.set_theme(name)
        self.apply_theme_to_widgets(self.controller)
        apply_ttk_theme(self.controller)

    def apply_theme_to_widgets(self, widget):

        if isinstance(widget, tk.Frame):
            widget.configure(bg=theme.THEME["bg"])

        elif isinstance(widget, tk.Label):
            widget.configure(
                bg=theme.THEME["bg"],
                fg=theme.THEME["text_primary"]
            )

        elif isinstance(widget, tk.Button):
            widget.configure(
                bg=theme.THEME["accent"],
                fg=theme.THEME["text_primary"],
                activebackground=theme.THEME["selected"],
                activeforeground=theme.THEME["text_primary_selected"]
            )

        elif isinstance(widget, tk.Entry):
            widget.configure(
                bg=theme.THEME["bg_highlight"],
                fg=theme.THEME["text_primary"],
                insertbackground=theme.THEME["text_primary"]
            )

        elif isinstance(widget, tk.Checkbutton):
            widget.configure(
                bg=theme.THEME["bg"],
                fg=theme.THEME["text_primary"],
                activebackground=theme.THEME["bg"]
            )
        elif isinstance(widget, tk.Spinbox):
            widget.configure(
                bg=theme.THEME["bg_highlight"],
                fg=theme.THEME["text_primary"],
                buttonbackground=theme.THEME["accent"]
            )

        for child in widget.winfo_children():
            self.apply_theme_to_widgets(child)

    def save_settings(self):
        settings["images_per_page"] = int(self.pp_var.get())
        settings["safe_mode"] = self.safe_var.get()
        tags = self.blacklist_var.get()
        settings["blacklisted_tags"] = [
            t.strip() for t in tags.split(",") if t.strip()
        ]
        settings["theme"] = self.theme_var.get()
        settings["version"] = ver
        
        save_settings(settings)

        messagebox.showinfo("Settings", "Saved.")

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    process_deletions()
    app = App()
    app.mainloop()
    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass
