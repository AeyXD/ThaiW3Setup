"""Locate The Witcher 3 installs (Steam, GOG, Epic, Xbox app) and identify the edition."""
from __future__ import annotations

import ctypes
import json
import logging
import os
import re
import string
from dataclasses import dataclass, field
from pathlib import Path

from .osutil import WINDOWS

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
    version: str = ""
    stale_content: list[str] = field(default_factory=list)
    loose_content: list[str] = field(default_factory=list)

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
            dirs = sorted((d for d in content.iterdir() if d.is_dir() and d.name.startswith("content")
                           and d.name not in self.stale_content),
                          key=lambda d: int(re.sub(r"\D", "", d.name) or 0))
            files += [d / name for d in dirs if (d / name).exists()]
        dlc = self.path / "dlc"
        if dlc.is_dir():
            for d in sorted(dlc.iterdir()):
                f = d / "content" / name
                if f.exists():
                    files.append(f)
        return files


def exe_version(path: Path) -> str:
    """File version of an exe as "a.b.c.d", or "" when unavailable (always so off Windows)."""
    try:
        ver = ctypes.windll.version
        size = ver.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return ""
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(str(path), 0, size, buf):
            return ""
        ptr, length = ctypes.c_void_p(), ctypes.c_uint()
        if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)):
            return ""
        ms, ls = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32 * 13)).contents[2:4]
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except (AttributeError, OSError):
        return ""


def _launcher_remastered(p: Path) -> bool:
    cfg = p / "launcher-configuration.json"
    if not cfg.exists():
        return False
    try:
        data = json.loads(cfg.read_text(encoding="utf-8-sig"))
        return any(e.get("name") == "remasteredEdition" for e in data.get("editions", []))
    except (OSError, ValueError, AttributeError) as exc:
        log.warning("cannot read %s: %s", cfg, exc)
        return False


def _split_content_dirs(p: Path) -> list[str]:
    """content1, content2, ... : the 4.x layout; 5.x ships everything in content0."""
    content = p / "content"
    dirs = [d.name for d in content.iterdir() if d.is_dir() and re.fullmatch(r"content[1-9]\d*", d.name)]
    return sorted(dirs, key=lambda n: int(n[7:]))


def _loose_content(p: Path) -> list[str]:
    """Mod files unpacked straight into content\\ (blob0.bundle, tr.w3strings, scripts\\) instead of mods\\."""
    content = p / "content"
    return sorted(e.name for e in content.iterdir()
                  if (e.is_dir() and e.name.lower() == "scripts")
                  or (e.is_file() and e.suffix.lower() in (".bundle", ".w3strings")))


def stale_note(dirs: list[str]) -> str:
    names = dirs[0] if len(dirs) == 1 else f"{dirs[0]}-{dirs[-1]}"
    return f"พบโฟลเดอร์ content\\{names} ที่ค้างจากเวอร์ชัน 4.x ลบทิ้งได้ (ห้ามลบ content0)"


def loose_note(names: list[str]) -> str:
    return (f"พบไฟล์ mod วางอยู่ในโฟลเดอร์ content โดยตรง ({', '.join(names)}) น่าจะติดตั้ง mod ผิดที่"
            " ควรย้ายออก (ห้ามลบ content0 และ metadata.store)")


XBOX_BIN = "gaming.desktop.x64"


def _find_exe(p: Path) -> Path | None:
    for sub in ("x64_dx12", "x64", XBOX_BIN):
        exe = p / "bin" / sub / "witcher3.exe"
        if exe.exists():
            return exe
    try:
        return next(iter(sorted((p / "bin").glob("*/witcher3.exe"))), None)
    except OSError:
        return None


def _is_xbox_build(p: Path) -> bool:
    """Xbox app (GDK) build; Windows hides its exe unless the folder is opened from the Xbox app."""
    return (p / "bin" / XBOX_BIN).is_dir()


def _is_game_dir(p: Path) -> bool:
    return (p / "content" / "content0").is_dir() and (_find_exe(p) is not None or _is_xbox_build(p))


def game_root(path: Path | str) -> Path:
    """The folder holding bin\\ and content\\.

    Xbox app installs keep them one level down in Content\\; also accepts a folder picked
    too deep (bin\\x64_dx12, content\\content0) or the XboxGames folder itself.
    """
    p = Path(path)
    if _is_game_dir(p):
        return p
    tries = [p / "Content", *list(p.parents)[:2]]
    try:
        tries += [d / "Content" for d in sorted(p.iterdir()) if d.is_dir() and "witcher 3" in d.name.lower()]
    except OSError:
        pass
    return next((t for t in tries if _is_game_dir(t)), p)


def _describe(p: Path) -> str:
    try:
        return ", ".join(sorted(e.name + ("\\" if e.is_dir() else "") for e in p.iterdir())) or "(empty)"
    except OSError as exc:
        return f"cannot list: {exc}"


def identify(path: Path | str, store: str = "") -> GameInfo:
    p = game_root(path)
    if not _is_game_dir(p):
        log.info("not a Witcher 3 folder: %s [%s]", p, _describe(p))
        return GameInfo(p, EDITION_UNKNOWN, store)

    exe = _find_exe(p)
    xbox = _is_xbox_build(p)
    version = exe_version(exe) if exe else ""
    split = _split_content_dirs(p)
    major = int(version.split(".")[0]) if version else 0
    if major >= 5:
        edition = EDITION_REMASTERED
    elif major == 4:
        edition = EDITION_NEXTGEN
    elif major:
        edition = EDITION_CLASSIC
    elif (_launcher_remastered(p) or xbox) and not split:
        edition = EDITION_REMASTERED
    elif xbox or (p / "bin" / "x64_dx12" / "witcher3.exe").exists():
        edition = EDITION_NEXTGEN
    else:
        edition = EDITION_CLASSIC
    if xbox and not version:
        log.info("Xbox build without a readable exe, edition from content layout: %s (%s)", p, edition)

    info = GameInfo(p, edition, store, version=version)
    if edition == EDITION_REMASTERED and split:
        info.stale_content = split
        info.notes.append(stale_note(split))
    if edition == EDITION_REMASTERED:
        info.loose_content = _loose_content(p)
        if info.loose_content:
            info.notes.append(loose_note(info.loose_content))
    return info


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


def _xbox_roots(drive: Path) -> list[Path]:
    """XboxGames plus any install folders the Xbox app recorded in <drive>\\.GamingRoot."""
    roots = [drive / "XboxGames"]
    try:
        data = (drive / ".GamingRoot").read_bytes()
    except OSError:
        return roots
    if data[:4] == b"RGBX":
        for name in data[8:].decode("utf-16-le", errors="ignore").split("\0"):
            name = name.strip().lstrip("\\")
            if name:
                roots.append(drive / name)
    return roots


def _xbox_candidates() -> list[Path]:
    out = []
    for letter in string.ascii_uppercase[2:]:
        drive = Path(f"{letter}:\\")
        if not drive.exists():
            continue
        for root in _xbox_roots(drive):
            try:
                if root.is_dir():
                    out += [d for d in sorted(root.iterdir()) if d.is_dir() and "witcher 3" in d.name.lower()]
            except OSError as exc:
                log.warning("cannot list %s: %s", root, exc)
    log.info("Xbox candidates: %s", [str(c) for c in out])
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
    """Installs we can find on our own. Off Windows every source is a dead end, so the user browses instead."""
    seen = set()
    found = []
    sources = (("Steam", _steam_candidates), ("GOG", _gog_candidates),
               ("Epic", _epic_candidates), ("Xbox", _xbox_candidates), ("", _drive_guesses)) if WINDOWS else ()
    for store, fn in sources:
        try:
            candidates = fn()
        except Exception as exc:  # detection must never crash the app
            log.warning("%s detection failed: %s", store or "drive", exc)
            continue
        for c in candidates:
            try:
                key = str(c.resolve()).lower()
                if key in seen or not c.is_dir():
                    continue
                seen.add(key)
                info = identify(c, store)
            except OSError as exc:
                log.warning("cannot check %s: %s", c, exc)
                continue
            if info.edition != EDITION_UNKNOWN:
                found.append(info)
    found.sort(key=lambda g: (not g.supported, g.edition != EDITION_REMASTERED))
    return found
