"""Check GitHub Releases for a newer version of this setup. Notifies only; never downloads or runs files."""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass

from . import APP_NAME, __version__
from .paths import app_data_dir

log = logging.getLogger(__name__)

REPO = "FordenHillson/ThaiW3Setup"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"
STATE_NAME = "update_state.json"


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


def _state_path():
    return app_data_dir() / STATE_NAME


def skipped_version() -> str:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8")).get("skip", "")
    except (OSError, ValueError):
        return ""


def skip_version(version: str) -> None:
    _state_path().write_text(json.dumps({"skip": version}), encoding="utf-8")


def check_for_update(respect_skip: bool = True) -> UpdateInfo | None:
    """Newer release, or None if up to date / skipped. Network errors propagate."""
    info = fetch_latest()
    if not info.newer:
        return None
    if respect_skip and info.version == skipped_version():
        return None
    return info
