"""Locate The Witcher 3 installs (Steam, GOG, Epic) and identify the edition."""
from __future__ import annotations

import json
import logging
import os
import re
import string
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

STEAM_APP_ID = "292030"
EDITION_REMASTERED = "remastered"
EDITION_NEXTGEN = "nextgen"
EDITION_CLASSIC = "classic"
EDITION_UNKNOWN = "unknown"

EDITION_LABELS = {
    EDITION_REMASTERED: "The Witcher 3: Wild Hunt - Remastered",
    EDITION_NEXTGEN: "The Witcher 3 Next-Gen (4.x) - ให้ใช้ w3tu ตัวเดิม",
    EDITION_CLASSIC: "The Witcher 3 เวอร์ชันเก่า (1.3x) - ไม่รองรับ",
    EDITION_UNKNOWN: "ไม่พบเกม The Witcher 3 ในโฟลเดอร์นี้",
}


@dataclass
class GameInfo:
    path: Path
    edition: str
    store: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def supported(self) -> bool:
        return self.edition == EDITION_REMASTERED

    @property
    def label(self) -> str:
        return EDITION_LABELS[self.edition]

    @property
    def content0(self) -> Path:
        return self.path / "content" / "content0"

    @property
    def mods_dir(self) -> Path:
        return self.path / "mods"

    @property
    def script_modules(self) -> Path:
        return self.content0 / "scripts" / "game" / "gui" / "hud" / "modules"

    def strings_files(self, language: str) -> list[Path]:
        """All base-game .w3strings for a language, lowest priority first."""
        name = f"{language}.w3strings"
        files = []
        content = self.path / "content"
        if content.is_dir():
            dirs = sorted((d for d in content.iterdir() if d.is_dir() and d.name.startswith("content")),
                          key=lambda d: int(re.sub(r"\D", "", d.name) or 0))
            files += [d / name for d in dirs if (d / name).exists()]
        dlc = self.path / "dlc"
        if dlc.is_dir():
            for d in sorted(dlc.iterdir()):
                f = d / "content" / name
                if f.exists():
                    files.append(f)
        return files


def identify(path: Path | str, store: str = "") -> GameInfo:
    p = Path(path)
    exe_dx12 = p / "bin" / "x64_dx12" / "witcher3.exe"
    exe_dx11 = p / "bin" / "x64" / "witcher3.exe"
    content0 = p / "content" / "content0"
    if not content0.is_dir() or not (exe_dx12.exists() or exe_dx11.exists()):
        return GameInfo(p, EDITION_UNKNOWN, store)

    remastered = False
    cfg = p / "launcher-configuration.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8-sig"))
            remastered = any(e.get("name") == "remasteredEdition" for e in data.get("editions", []))
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %s", cfg, exc)
    has_split_content = (p / "content" / "content1").is_dir()

    if remastered and not has_split_content:
        return GameInfo(p, EDITION_REMASTERED, store)
    if exe_dx12.exists():
        return GameInfo(p, EDITION_NEXTGEN, store)
    return GameInfo(p, EDITION_CLASSIC, store)


def _reg_value(root, key: str, name: str) -> str | None:
    try:
        import winreg
        with winreg.OpenKey(root, key) as k:
            return str(winreg.QueryValueEx(k, name)[0])
    except OSError:
        return None


def _steam_candidates() -> list[Path]:
    roots = []
    try:
        import winreg
        for root, key, name in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ):
            v = _reg_value(root, key, name)
            if v:
                roots.append(Path(v))
    except ImportError:
        pass
    libraries = []
    for root in roots:
        libraries.append(root)
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            text = vdf.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                libraries.append(Path(m.group(1).replace("\\\\", "\\")))
    out = []
    for lib in libraries:
        manifest = lib / "steamapps" / f"appmanifest_{STEAM_APP_ID}.acf"
        installdir = "The Witcher 3"
        if manifest.exists():
            m = re.search(r'"installdir"\s+"([^"]+)"', manifest.read_text(encoding="utf-8", errors="replace"))
            if m:
                installdir = m.group(1)
        out.append(lib / "steamapps" / "common" / installdir)
    return out


def _gog_candidates() -> list[Path]:
    out = []
    try:
        import winreg
        base = r"SOFTWARE\WOW6432Node\GOG.com\Games"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as k:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                name = _reg_value(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{sub}", "gameName") or ""
                if "witcher 3" in name.lower():
                    path = _reg_value(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{sub}", "path")
                    if path:
                        out.append(Path(path))
    except (ImportError, OSError):
        pass
    return out


def _epic_candidates() -> list[Path]:
    out = []
    manifests = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    if manifests.is_dir():
        for item in manifests.glob("*.item"):
            try:
                data = json.loads(item.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if "witcher 3" in str(data.get("DisplayName", "")).lower():
                loc = data.get("InstallLocation")
                if loc:
                    out.append(Path(loc))
    return out


def _drive_guesses() -> list[Path]:
    out = []
    for letter in string.ascii_uppercase[2:]:
        drive = Path(f"{letter}:\\")
        if not drive.exists():
            continue
        for rel in (r"SteamLibrary\steamapps\common\The Witcher 3",
                    r"Program Files (x86)\Steam\steamapps\common\The Witcher 3",
                    r"GOG Games\The Witcher 3 Wild Hunt GOTY",
                    r"Games\The Witcher 3"):
            out.append(drive / rel)
    return out


def find_games() -> list[GameInfo]:
    seen = set()
    found = []
    sources = (("Steam", _steam_candidates), ("GOG", _gog_candidates),
               ("Epic", _epic_candidates), ("", _drive_guesses))
    for store, fn in sources:
        try:
            candidates = fn()
        except Exception as exc:  # detection must never crash the app
            log.warning("%s detection failed: %s", store or "drive", exc)
            continue
        for c in candidates:
            try:
                key = str(c.resolve()).lower()
            except OSError:
                continue
            if key in seen or not c.is_dir():
                continue
            seen.add(key)
            info = identify(c, store)
            if info.edition != EDITION_UNKNOWN:
                found.append(info)
    found.sort(key=lambda g: (not g.supported, g.edition != EDITION_REMASTERED))
    return found
