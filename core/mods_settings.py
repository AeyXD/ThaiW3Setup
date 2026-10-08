"""mods.settings in Documents/The Witcher 3: per-mod Enabled and Priority, written by the game's mod menu and by
The Witcher 3 Mod Manager. Read only; the Mod Manager rewrites it, so we never do.

A lower Priority wins. Mods without a Priority load after every mod that has one, in name order.
"""
from __future__ import annotations

import configparser
import ctypes
import logging
from dataclasses import dataclass
from pathlib import Path

from .osutil import WINDOWS
from .wine import bottle_of

log = logging.getLogger(__name__)

FILE_NAME = "mods.settings"


@dataclass(frozen=True)
class ModSetting:
    enabled: bool = True
    priority: int | None = None


def documents_dir() -> Path:
    if WINDOWS:  # Documents may be redirected to OneDrive or another drive
        try:
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return Path(buf.value)
        except (AttributeError, OSError):
            pass
    return Path.home() / "Documents"


def settings_paths(game_path: Path | None = None) -> list[Path]:
    """Where the game keeps mods.settings. Inside a bottle that is the bottle's own Documents."""
    paths = []
    bottle = bottle_of(game_path) if game_path is not None else None
    if bottle:
        paths += [d / "The Witcher 3" / FILE_NAME for d in bottle.documents_dirs()]
    paths.append(documents_dir() / "The Witcher 3" / FILE_NAME)
    paths.append(Path.home() / "Documents" / "The Witcher 3" / FILE_NAME)
    if WINDOWS:  # Documents redirected into OneDrive is a Windows arrangement
        paths.append(Path.home() / "OneDrive" / "Documents" / "The Witcher 3" / FILE_NAME)
    out: list[Path] = []
    for p in paths:
        if p not in out:
            out.append(p)
    return out


def _decode(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig", errors="replace")


def parse(text: str) -> dict[str, ModSetting]:
    """Settings keyed by lowercased mod folder name."""
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        log.warning("mods.settings unreadable: %s", exc)
        return {}
    out = {}
    for name in parser.sections():
        sec = {k.lower(): v.strip() for k, v in parser[name].items()}
        try:
            priority = int(sec["priority"]) if sec.get("priority") else None
        except ValueError:
            priority = None
        out[name.lower()] = ModSetting(sec.get("enabled", "1") != "0", priority)
    return out


def read(game_path: Path | None = None) -> dict[str, ModSetting]:
    """The first mods.settings found, empty when there is none."""
    for path in settings_paths(game_path):
        try:
            return parse(_decode(path.read_bytes()))
        except FileNotFoundError:
            continue
        except OSError as exc:
            log.warning("cannot read %s: %s", path, exc)
    return {}


def _rank(name: str, s: ModSetting) -> tuple:
    return (s.priority is None, s.priority if s.priority is not None else 0, name.lower())


def loses_to(patch: str, others: list[str], settings: dict[str, ModSetting]) -> list[str]:
    """The mods in others that load ahead of patch and so override its files."""
    mine = settings.get(patch.lower(), ModSetting())
    return [o for o in others
            if _rank(o, settings.get(o.lower(), ModSetting())) < _rank(patch, mine)]


def disabled(name: str, settings: dict[str, ModSetting]) -> bool:
    return not settings.get(name.lower(), ModSetting()).enabled
