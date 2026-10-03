"""Small Tk helpers: Material Symbols icons from assets/icons and hover tooltips."""
from __future__ import annotations

import logging
import tkinter as tk

from PIL import Image, ImageTk

from core.paths import assets_dir
from gui.theme import P, ui

log = logging.getLogger(__name__)

DISABLED_ALPHA = 0.35
_cache: dict[tuple[str, int, bool], ImageTk.PhotoImage] = {}


def icon(widget: tk.Misc, name: str, size: int = 20, disabled: bool = False) -> ImageTk.PhotoImage | None:
    """The icon scaled for the screen DPI, or None when the file is missing (callers fall back to text)."""
    px = max(8, round(size * widget.winfo_fpixels("1i") / 96))
    key = (name, px, disabled)
    if key not in _cache:
        try:
            img = Image.open(assets_dir() / "icons" / f"{name}.png").convert("RGBA").resize((px, px), Image.LANCZOS)
        except OSError as exc:
            log.warning("icon %s: %s", name, exc)
            return None
        if disabled:
            img.putalpha(img.getchannel("A").point(lambda a: int(a * DISABLED_ALPHA)))
        _cache[key] = ImageTk.PhotoImage(img, master=widget)
    return _cache[key]


def ttk_image(widget: tk.Misc, name: str, size: int = 20) -> tuple | str:
    """Value for a ttk widget's image option, dimmed while the widget is disabled."""
    normal = icon(widget, name, size)
    if normal is None:
        return ""
    return (normal, "disabled", icon(widget, name, size, disabled=True))


class Tooltip:
    DELAY_MS = 500

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        self.job: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self.job = self.widget.after(self.DELAY_MS, self._show)

    def _cancel(self):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None

    def _show(self):
        self.job = None
        if self.tip or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_attributes("-topmost", True)
        tk.Label(self.tip, text=self.text, background=P.tip_bg, foreground=P.tip_fg, relief="solid", borderwidth=1,
                 font=ui(9), padx=6, pady=2).pack()
        self.tip.update_idletasks()
        # keep the tip on screen when the button sits at the bottom edge
        if y + self.tip.winfo_height() > self.widget.winfo_screenheight():
            y = self.widget.winfo_rooty() - self.tip.winfo_height() - 4
        self.tip.wm_geometry(f"+{x}+{y}")

    def _hide(self, _event=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None
