"""Fonts, semantic colours and the ttk theme. Windows and Linux always use the dark Sun Valley theme;
macOS keeps aqua and follows the system appearance."""
from __future__ import annotations

import ctypes
import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont

from core.osutil import MACOS, WINDOWS

log = logging.getLogger(__name__)

if WINDOWS:
    UI, MONO = "Leelawadee UI", "Consolas"
elif MACOS:
    UI, MONO = ".AppleSystemUIFont", "Menlo"  # the system font covers Thai through its own fallback
else:
    UI, MONO = "Noto Sans Thai", "DejaVu Sans Mono"

# aqua draws its own controls; setting a font or padding on them makes ttk fall back to flat boxes
NATIVE_CONTROLS = MACOS
DARK_THEME = not MACOS
# the main action of a window; falls back to a plain button where the theme has no Accent style
BIG_BUTTON = "Big.Accent.TButton"
# Sun Valley dark surfaces, for the plain tk widgets the ttk theme does not reach
SURFACE = "#1c1c1c"
FIELD = "#2b2b2b"
TEXT = "#fafafa"
SELECT = "#2f60d8"
# the accent button sprites recoloured for destructive actions
DANGER_HUE = 0.99
DANGER_VALUE = 0.82


def ui(size: int, *style: str) -> tuple:
    return (UI, size, *style)


def mono(size: int, *style: str) -> tuple:
    return (MONO, size, *style)


@dataclass
class Palette:
    ok: str
    bad: str
    warn: str
    hint: str
    note: str
    accent: str
    link: str
    banner_bg: str
    banner_fg: str
    tip_bg: str
    tip_fg: str


LIGHT = Palette(ok="#1a7f37", bad="#c62828", warn="#b26a00", hint="#666666", note="#777777",
                accent="#1a5fb4", link="#5b3fc4", banner_bg="#fff4c2", banner_fg="#000000",
                tip_bg="#ffffe1", tip_fg="#000000")
DARK = Palette(ok="#4cc38a", bad="#ff6b5f", warn="#ffb340", hint="#9a9a9f", note="#8e8e93",
               accent="#57c8ff", link="#c79bff", banner_bg="#3a3320", banner_fg="#ffd60a",
               tip_bg="#2b2b2b", tip_fg="#f2f2f7")

# the one instance every module imports; init() fills it in place so those imports stay valid
P = Palette(**vars(LIGHT))


def init(root: tk.Tk) -> None:
    """Set up the theme and pick the palette. Call once the root window exists, before building widgets."""
    if DARK_THEME:
        _use_dark_theme(root)
    for name, value in vars(DARK if DARK_THEME or _dark(root) else LIGHT).items():
        setattr(P, name, value)


def _use_dark_theme(root: tk.Tk) -> None:
    import sv_ttk

    # the theme answers <<ThemeChanged>> with tk_setPalette, which later writes the palette into the
    # foreground of every label and hides the style colours; run it now, while there are no widgets yet
    sv_ttk.set_theme("dark", root)
    root.bind_class(root.winfo_class(), "<<ThemeChanged>>", "")
    root.tk.call("configure_colors")
    for widget in ("TLabel", "TEntry", "TCombobox"):
        root.option_add(f"*{widget}.foreground", "")
        root.option_add(f"*{widget}.background", "")
    # the theme's fonts are Segoe UI, which has no Thai
    for name in tkfont.names(root):
        if name.startswith("SunValley"):
            tkfont.nametofont(name, root).configure(family=UI)
    root.configure(background=SURFACE)
    for widget in ("Text", "Listbox", "Menu"):
        root.option_add(f"*{widget}.background", FIELD)
        root.option_add(f"*{widget}.foreground", TEXT)
        root.option_add(f"*{widget}.selectBackground", SELECT)
        root.option_add(f"*{widget}.selectForeground", TEXT)
    root.option_add("*Text.insertBackground", TEXT)
    root.option_add("*Text.relief", "flat")
    root.option_add("*Menu.activeBackground", SELECT)
    root.option_add("*Menu.activeForeground", TEXT)
    root.option_add("*Toplevel.background", SURFACE)
    try:
        _danger_button(root)
    except (tk.TclError, OSError, ValueError) as exc:
        log.info("danger button: %s", exc)
    dark_title_bar(root)
    root.bind_class("Toplevel", "<Map>", lambda e: dark_title_bar(e.widget), add="+")


DANGER_STATES = (("rest", ""), ("dis", "disabled"), ("pressed", "pressed"), ("focus-hover", "active focus"),
                 ("hover", "active"), ("focus", "focus"))


def _danger_button(root: tk.Tk) -> None:
    """Danger.TButton: the theme's accent button sprites turned red."""
    import colorsys

    from PIL import Image, ImageTk

    tcl = root.tk
    images = {}
    for name, _state in DANGER_STATES:
        src = tcl.eval(f"set ttk::theme::sv_dark::I(button-accent-{name})")
        width, height = int(tcl.call("image", "width", src)), int(tcl.call("image", "height", src))
        img = Image.new("RGBA", (width, height))
        px = img.load()
        for y in range(height):
            for x in range(width):
                # Tk 8.6 photos cannot export PNG, so read them a pixel at a time; these sprites are tiny
                if tcl.getboolean(tcl.call(src, "transparency", "get", x, y)):
                    continue
                r, g, b = (int(c) for c in tcl.splitlist(tcl.call(src, "get", x, y)))
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                r, g, b = colorsys.hsv_to_rgb(DANGER_HUE, s, v * DANGER_VALUE)
                px[x, y] = (round(r * 255), round(g * 255), round(b * 255), 255)
        images[name] = ImageTk.PhotoImage(img, master=root)
    root._danger_images = images  # Tk drops images Python no longer holds
    spec = [str(images["rest"])]
    for name, state in DANGER_STATES[1:]:
        spec += [state, str(images[name])]
    tcl.call("ttk::style", "element", "create", "DangerButton.button", "image", spec,
             "-border", 4, "-sticky", "nsew")
    tcl.eval("ttk::style layout Danger.TButton {DangerButton.button -children {DangerButton.padding "
             "-children {DangerButton.label -side left -expand 1}}}")
    tcl.call("ttk::style", "configure", "Danger.TButton", "-padding", "8 2 8 3", "-anchor", "center",
             "-foreground", "#ffffff")
    tcl.call("ttk::style", "map", "Danger.TButton", "-foreground", ["pressed", "#f3c9c5", "disabled", "#a5a5a5"])


def dark_title_bar(window: tk.Misc) -> None:
    """Ask Windows 10 / 11 for a dark title bar on this window."""
    if not WINDOWS or not isinstance(window, (tk.Tk, tk.Toplevel)):
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        on = ctypes.c_int(1)
        # DWMWA_USE_IMMERSIVE_DARK_MODE is 20 on Windows 10 20H1 and later, 19 before
        for attribute in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
    except (AttributeError, OSError, tk.TclError) as exc:
        log.info("dark title bar: %s", exc)


def _dark(root: tk.Misc) -> bool:
    if not MACOS:
        return False
    try:
        return bool(int(root.tk.eval("tk::unsupported::MacWindowStyle isdark .")))
    except tk.TclError:
        return False
