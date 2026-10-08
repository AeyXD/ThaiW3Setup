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
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
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


def _get(url: str, timeout: float):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{__version__}",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _info(data: dict, download_url: str) -> UpdateInfo:
    return UpdateInfo(
        version=str(data.get("tag_name", "")).lstrip("v"),
        notes=str(data.get("body") or "").strip(),
        page_url=str(data.get("html_url") or RELEASES_URL),
        download_url=download_url,
    )


def fetch_latest(timeout: float = 8.0) -> UpdateInfo | None:
    """The newest release carrying this platform's build, or None when there is none."""
    if not MACOS:
        data = _get(LATEST_URL, timeout)
        return _info(data, pick_download(data.get("assets", [])) or RELEASES_URL)
    # a release whose macOS build failed carries only the Windows zip; /releases/latest would offer
    # it anyway, so look through the list (pre-releases included) for the newest one with ours
    found = []
    for data in _get(RELEASES_API, timeout):
        if data.get("draft"):
            continue
        url = pick_download(data.get("assets", []))
        if url:
            found.append(_info(data, url))
    return max(found, key=lambda i: parse_version(i.version), default=None)


def pick_download(assets: list[dict]) -> str:
    """The zip built for this platform, or "" when the release has none; the other platform's zip is never it."""
    for a in assets:
        name = str(a.get("name") or "").lower()
        if name.endswith(".zip") and (MAC_TAG in name) == MACOS:
            return str(a.get("browser_download_url") or "")
    return ""


def check_for_update() -> UpdateInfo | None:
    """Newer release, or None if up to date. Network errors propagate."""
    info = fetch_latest()
    return info if info and info.newer else None
