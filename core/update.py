"""Check GitHub Releases for a newer version of this setup. Notifies only; never downloads or runs files."""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass

from . import APP_NAME, __version__
from .osutil import MACOS
log = logging.getLogger(__name__)

REPO = "FordenHillson/ThaiW3Setup"
# the macOS build carries the tag in its file name; the Windows one is just ThaiW3Setup-<version>.zip
MAC_TAG = "macos"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"


@dataclass
class UpdateInfo:
    version: str
    notes: str
    page_url: str
    download_url: str

    @property
    def newer(self) -> bool:
        return parse_version(self.version) > parse_version(__version__)


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", text)[:4]) or (0,)


def fetch_latest(timeout: float = 8.0) -> UpdateInfo:
    req = urllib.request.Request(LATEST_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{__version__}",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return UpdateInfo(
        version=str(data.get("tag_name", "")).lstrip("v"),
        notes=str(data.get("body") or "").strip(),
        page_url=str(data.get("html_url") or RELEASES_URL),
        download_url=pick_download(data.get("assets", [])) or str(data.get("html_url") or RELEASES_URL),
    )


def pick_download(assets: list[dict]) -> str:
    """The zip built for this platform. A release holding only the other one still links somewhere useful."""
    zips = [a for a in assets if str(a.get("name") or "").lower().endswith(".zip")]
    ours = [a for a in zips if (MAC_TAG in str(a.get("name") or "").lower()) == MACOS]
    chosen = ours or zips
    return str(chosen[0].get("browser_download_url") or "") if chosen else ""


def check_for_update() -> UpdateInfo | None:
    """Newer release, or None if up to date. Network errors propagate."""
    info = fetch_latest()
    return info if info.newer else None
