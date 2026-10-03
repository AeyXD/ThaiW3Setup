"""Modal notice with an optional picture and a "don't show again" check box."""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from gui.theme import P, ui

log = logging.getLogger(__name__)

T_DONT_SHOW = "\u0e44\u0e21\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e41\u0e2a\u0e14\u0e07\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e19\u0e35\u0e49\u0e2d\u0e35\u0e01"
T_OK = "\u0e15\u0e01\u0e25\u0e07"
IMAGE_MAX_W = 640
TEXT_W = 620
MESSAGE_BOLD = ui(10, "bold")
WARNING_FONT = ui(13, "bold")


def _photo(path: Path) -> ImageTk.PhotoImage | None:
    try:
        img = Image.open(path).convert("RGB")
    except OSError as exc:
        log.warning("notice image %s: %s", path, exc)
        return None
    if img.width > IMAGE_MAX_W:
        img = img.resize((IMAGE_MAX_W, round(img.height * IMAGE_MAX_W / img.width)), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


class NoticeDialog(tk.Toplevel):
    def __init__(self, parent, title: str, message: str, image: Path | None = None, bold: bool = False,
                 warning: str | None = None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.v_hide = tk.BooleanVar(value=False)

        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        label = ttk.Label(root, text=message, wraplength=TEXT_W, justify="left")
        if bold:
            label.configure(font=MESSAGE_BOLD)
        label.pack(anchor="w")
        if warning:
            ttk.Label(root, text=warning, wraplength=TEXT_W, justify="left", font=WARNING_FONT,
                      foreground=P.bad).pack(anchor="w", pady=(10, 0))
        self.photo = _photo(image) if image else None
        if self.photo is not None:
            ttk.Label(root, image=self.photo, relief="solid", borderwidth=1).pack(pady=(10, 0))
        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Checkbutton(bottom, text=T_DONT_SHOW, variable=self.v_hide).pack(side="left")
        ok = ttk.Button(bottom, text=T_OK, command=self.destroy)
        ok.pack(side="right")

        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        ok.focus_set()
        self.grab_set()


def show_notice(parent, title: str, message: str, image: Path | None = None, bold: bool = False,
                warning: str | None = None) -> bool:
    """Show the notice and wait; True when the user ticked "don't show again"."""
    dialog = NoticeDialog(parent, title, message, image, bold, warning)
    hide = dialog.v_hide
    parent.wait_window(dialog)
    return bool(hide.get())
