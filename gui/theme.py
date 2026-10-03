"""Fonts and semantic colours. On macOS they follow the system appearance; Windows keeps its own look."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from core.osutil import MACOS, WINDOWS

if WINDOWS:
    UI, MONO = "Leelawadee UI", "Consolas"
elif MACOS:
    UI, MONO = ".AppleSystemUIFont", "Menlo"  # the system font covers Thai through its own fallback
else:
    UI, MONO = "Noto Sans Thai", "DejaVu Sans Mono"

# aqua draws its own controls; setting a font or padding on them makes ttk fall back to flat boxes
NATIVE_CONTROLS = MACOS


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
DARK = Palette(ok="#30d158", bad="#ff453a", warn="#ff9f0a", hint="#98989d", note="#8e8e93",
               accent="#0a84ff", link="#bf5af2", banner_bg="#3a3320", banner_fg="#ffd60a",
               tip_bg="#2c2c2e", tip_fg="#f2f2f7")

# the one instance every module imports; init() fills it in place so those imports stay valid
P = Palette(**vars(LIGHT))


def init(root: tk.Misc) -> None:
    """Pick the palette for the current system appearance. Call once the root window exists."""
    for name, value in vars(DARK if _dark(root) else LIGHT).items():
        setattr(P, name, value)


def _dark(root: tk.Misc) -> bool:
    if not MACOS:
        return False
    try:
        return bool(int(root.tk.eval("tk::unsupported::MacWindowStyle isdark .")))
    except tk.TclError:
        return False
