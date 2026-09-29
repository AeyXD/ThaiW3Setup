"""Check GitHub Releases for a newer version of this setup. Notifies only; never downloads or runs files."""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass

from . import APP_NAME, __version__
log = logging.getLogger(__name__)

REPO = "FordenHillson/ThaiW3Setup"
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
    zips = [a["browser_download_url"] for a in data.get("assets", []) if a.get("name", "").endswith(".zip")]
    return UpdateInfo(
        version=str(data.get("tag_name", "")).lstrip("v"),
        notes=str(data.get("body") or "").strip(),
        page_url=str(data.get("html_url") or RELEASES_URL),
        download_url=zips[0] if zips else str(data.get("html_url") or RELEASES_URL),
    )


def check_for_update() -> UpdateInfo | None:
    """Newer release, or None if up to date. Network errors propagate."""
    info = fetch_latest()
    return info if info.newer else None
