"""The handful of places where Windows and macOS differ; everything else is plain pathlib."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"


def open_folder(path: Path | str) -> None:
    """Show a folder in Explorer / Finder. Never raises; a failure is only a convenience lost."""
    try:
        if WINDOWS:
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["open" if MACOS else "xdg-open", str(path)], check=False)
    except OSError as exc:
        log.warning("cannot open %s: %s", path, exc)
