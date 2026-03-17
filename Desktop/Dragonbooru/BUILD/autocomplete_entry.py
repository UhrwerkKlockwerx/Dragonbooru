from db import autocomplete_tags
import tkinter as tk

class AutocompleteEntry(tk.Entry):
    """Tkinter Entry widget with autocomplete from a SQLite tags table."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.listbox = None
        self.matches = []

        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<Down>", self._on_down)
        self.bind("<Up>", self._on_up)
        self.bind("<Return>", self._on_enter)
        self.bind("<Escape>", lambda e: self.hide_listbox())
        self.bind("<FocusOut>", self._check_focus_out)

        # Optional: hide listbox when clicking outside the entry/listbox
        self.master.winfo_toplevel().bind("<Button-1>", self._check_click_outside)

    # Key handling
    def _on_keyrelease(self, event):
        if event.keysym in ("Down", "Up", "Return", "Escape"):
            return
        self._update_matches()

    def _update_matches(self):
        text = self.get().split(",")[-1].strip()
        if not text:
            self.hide_listbox()
            return

        self.matches = autocomplete_tags(text)

        if self.matches:
            self.show_listbox()
        else:
            self.hide_listbox()

    def _on_down(self, event):
        if not self.listbox:
            return "break"
        cur_sel = self.listbox.curselection()
        if not cur_sel:
            self.listbox.select_set(0)
        else:
            idx = cur_sel[0]
            if idx < self.listbox.size() - 1:
                self.listbox.select_clear(idx)
                self.listbox.select_set(idx + 1)
        self.listbox.activate(tk.ACTIVE)
        return "break"

    def _on_up(self, event):
        if not self.listbox:
            return "break"
        cur_sel = self.listbox.curselection()
        if not cur_sel:
            self.listbox.select_set(0)
        else:
            idx = cur_sel[0]
            if idx > 0:
                self.listbox.select_clear(idx)
                self.listbox.select_set(idx - 1)
        self.listbox.activate(tk.ACTIVE)
        return "break"

    def _on_enter(self, event):
        if self.listbox and self.listbox.curselection():
            self._select_current()
            return "break"
        elif self.listbox and self.matches:
            # if listbox is open but nothing is selected, default to the first option
            self.listbox.select_set(0)
            self._select_current()
            return "break"
        # o/w do nothing and allow normal Enter behaviour

    # Listbox display
    def show_listbox(self):
        if not self.listbox:
            self.listbox = tk.Listbox(self.master.winfo_toplevel(), height=6)
            self.listbox.bind("<ButtonRelease-1>", lambda e: self._select_current())
        self.listbox.delete(0, tk.END)
        for m in self.matches:
            self.listbox.insert(tk.END, m)

        # Position below entry
        self.listbox.place(
            x=self.winfo_rootx() - self.master.winfo_rootx(),
            y=self.winfo_rooty() - self.master.winfo_rooty() + self.winfo_height()
        )

    def hide_listbox(self):
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None

    # Selection
    def _select_current(self):
        if not self.listbox:
            return
        sel = self.listbox.get(self.listbox.curselection())
        text = self.get()
        if "," in text:
            parts = text.split(",")
            parts[-1] = sel
            new_text = ", ".join([p.strip() for p in parts])
        else:
            new_text = sel
        new_text += ", "
        self.delete(0, tk.END)
        self.insert(0, new_text)
        self.icursor(tk.END)
        self.hide_listbox()

    # Focus handling
    def _check_focus_out(self, event):
        try:
            focused = self.master.focus_get()
        except Exception:
            focused = None
        # Only hide if focus left both entry and listbox
        if self.listbox and focused not in (self, self.listbox):
            self.hide_listbox()

    def _check_click_outside(self, event):
        widget = event.widget
        if widget not in (self, self.listbox):
            self.hide_listbox()
