from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME
from .osutil import MACOS, WINDOWS


def assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "assets"


def app_data_dir() -> Path:
    """Settings and cache; THAIW3SETUP_DATA overrides it so tests stay out of the real profile."""
    override = os.environ.get("THAIW3SETUP_DATA")
    if override:
        path = Path(override)
    else:
        if WINDOWS:
            root = Path(os.environ.get("APPDATA") or Path.home())
        elif MACOS:
            root = Path.home() / "Library" / "Application Support"
        else:
            root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def app_data_label() -> str:
    """How to name the settings folder in a message. Windows users know %APPDATA% already."""
    return "%APPDATA%" if WINDOWS else str(app_data_dir())


def cache_dir() -> Path:
    path = app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path
