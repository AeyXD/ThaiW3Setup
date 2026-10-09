"""Wine prefixes on macOS. The game has no Mac build, so a Mac player's copy lives inside a bottle.

A prefix is a folder holding drive_c/ next to dosdevices/, where each drive letter is a symlink, and
system.reg / user.reg hold the same registry the Windows build reads.
"""
from __future__ import annotations

import functools
import json
import logging
import os
import plistlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

log = logging.getLogger(__name__)

HOME = Path.home()
# Whisky was archived under its original id; the maintained fork ships under its own
WHISKY_IDS = ("com.isaacmarovitz.Whisky", "com.franke.Whisky")
CONTAINERS = HOME / "Library/Containers"
HEROIC_DIR = HOME / "Library/Application Support/heroic"
# each entry holds one prefix, or a folder of them; Heroic keeps its prefix one level down in pfx/
BOTTLE_ROOTS = (
    (HOME / "Library/Application Support/CrossOver/Bottles", "CrossOver"),
    *((CONTAINERS / app / "Bottles", "Whisky") for app in WHISKY_IDS),
    (HOME / "Library/Application Support/Whisky/Bottles", "Whisky"),
    (HOME / "Games/Heroic/Prefixes", "Heroic"),  # Heroic 2.x: one prefix per game, named after it
    (HOME / "Games/Heroic/Prefixes/default", "Heroic"),
    (HOME / "Library/Application Support/heroic/Prefixes/default", "Heroic"),
    (HOME / "Library/Application Support/PortingKit/Bottles", "Porting Kit"),
    (HOME / ".wine", "Wine"),
)
HIVES = {"machine": "system.reg", "user": "user.reg"}
DRIVE = re.compile(r"^([A-Za-z]):[\\/](.*)$", re.S)


@dataclass(frozen=True)
class Bottle:
    prefix: Path
    kind: str

    @property
    def label(self) -> str:
        return f"{self.kind}: {self.name}"

    @property
    def name(self) -> str:
        """Whisky names the folder with a UUID and keeps the name the user typed in Metadata.plist."""
        info = _read_plist(self.prefix / "Metadata.plist").get("info")
        name = info.get("name") if isinstance(info, dict) else None
        return name if isinstance(name, str) and name else self.prefix.name

    def pinned_programs(self) -> list[Path]:
        """Programs Whisky pinned in this bottle; it pins every exe the user runs from outside the bottle."""
        info = _read_plist(self.prefix / "Metadata.plist").get("info")
        pins = info.get("pins") if isinstance(info, dict) else None
        out = []
        for pin in pins if isinstance(pins, list) else []:
            url = pin.get("url") if isinstance(pin, dict) else None
            path = _file_url(url.get("relative") if isinstance(url, dict) else url)
            path = _true_case(path) if path else None  # Whisky may record a lowercased path
            if path and path not in out:
                out.append(path)
        return out

    @property
    def drive_c(self) -> Path:
        return self.prefix / "drive_c"

    def host_path(self, windows_path: str) -> Path | None:
        """Translate "D:\\Games\\x" into a path on this Mac, or None when the drive is not mapped."""
        m = DRIVE.match(windows_path.strip())
        if not m:
            return None
        letter, rest = m.group(1).lower(), m.group(2).replace("\\", "/")
        root = self.prefix / "dosdevices" / f"{letter}:"
        if root.is_symlink() or root.is_dir():
            root = root.resolve()
        elif letter == "c":
            root = self.drive_c
        else:
            return None
        return _walk_insensitive(root, [p for p in rest.split("/") if p])

    def registry(self, hive: str, key: str, name: str) -> str | None:
        """A string value out of system.reg / user.reg, the way _reg_value reads the real registry."""
        return _reg_lookup(_hive_text(self.prefix / HIVES[hive]), key, name)

    def registry_keys(self, hive: str, under: str) -> list[str]:
        """Names of the subkeys directly under `under`, lowercased."""
        text = _hive_text(self.prefix / HIVES[hive])
        prefix = _reg_norm(under) + "\\"
        out = []
        for section in re.findall(r"^\[(.+?)\]", text, re.M):
            norm = _reg_norm(_reg_unescape(section))
            if norm.startswith(prefix):
                child = norm[len(prefix):].split("\\")[0]
                if child and child not in out:
                    out.append(child)
        return out

    def drives(self) -> list[Path]:
        """Where each mapped drive letter actually points on this Mac."""
        out = []
        dos = self.prefix / "dosdevices"
        try:
            entries = sorted(dos.iterdir()) if dos.is_dir() else []
        except OSError:
            entries = []
        for entry in entries:
            if re.fullmatch(r"[a-z]:", entry.name):
                try:
                    target = entry.resolve()
                except OSError:
                    continue
                if target.is_dir() and target not in out:
                    out.append(target)
        if self.drive_c.is_dir() and self.drive_c.resolve() not in out:
            out.append(self.drive_c.resolve())
        return out

    def documents_dirs(self) -> list[Path]:
        """Documents of every user in the bottle; that is where mods.settings lives."""
        users = self.drive_c / "users"
        if not users.is_dir():
            return []
        out = []
        # Public is shared by everyone; the game writes into the user's own Documents
        for user in sorted(users.iterdir(), key=lambda u: (u.name.lower() == "public", u.name)):
            docs = user / "Documents"
            if docs.is_dir():
                out.append(docs)
        return out


def _read_plist(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            data = plistlib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, plistlib.InvalidFileException) as exc:
        log.warning("cannot read %s: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        log.warning("cannot read %s: %s", path, exc)
        return None


def _file_url(value) -> Path | None:
    """Whisky stores paths as file:// URLs."""
    if not isinstance(value, str) or not value:
        return None
    if value.startswith("file:"):
        return Path(unquote(urlparse(value).path))
    return Path(value) if value.startswith("/") else None


def _hive_text(path: Path) -> str:
    """A .reg file runs to megabytes and every lookup scans it, so read each one once per revision."""
    try:
        stat = path.stat()
    except OSError:
        return ""
    return _read_hive(str(path), stat.st_mtime_ns, stat.st_size)


@functools.lru_cache(maxsize=16)
def _read_hive(path: str, mtime_ns: int, size: int) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("cannot read %s: %s", path, exc)
        return ""


def _reg_norm(key: str) -> str:
    return key.strip("\\").lower()


def _reg_unescape(text: str) -> str:
    return text.replace("\\\\", "\\")


def _reg_lookup(text: str, key: str, name: str) -> str | None:
    wanted_key, wanted_name = _reg_norm(key), name.lower()
    in_section = False
    for line in text.splitlines():
        if line.startswith("["):
            section = line[1:line.index("]")] if "]" in line else ""
            in_section = _reg_norm(_reg_unescape(section)) == wanted_key
        elif in_section and line.startswith('"'):
            m = re.match(r'"(.*?)"\s*=\s*"(.*)"\s*$', line)
            if m and m.group(1).lower() == wanted_name:
                return _reg_unescape(m.group(2))
    return None


def _walk_insensitive(root: Path, parts: list[str]) -> Path:
    """Join `parts` onto root. A component that exists under another casing still resolves; the caller
    decides whether the result is there, so anything past the end of the tree is joined as written."""
    current = root
    for i, part in enumerate(parts):
        if (current / part).exists():
            current = current / part
            continue
        try:
            match = next((c for c in current.iterdir() if c.name.lower() == part.lower()), None)
        except OSError:
            match = None
        if match is None:
            return current.joinpath(*parts[i:])
        current = match
    return current


def _true_case(path: Path) -> Path:
    """The same path spelled the way the disk spells it; macOS matches names case-insensitively."""
    if not path.is_absolute():
        return path
    current = Path(path.anchor)
    parts = path.parts[1:]
    for i, part in enumerate(parts):
        try:
            names = os.listdir(current)
        except OSError:
            return current.joinpath(*parts[i:])
        if part not in names:  # exists() alone cannot tell, it matches any casing
            part = next((n for n in names if n.lower() == part.lower()), part)
        current = current / part
    return current


def _prefixes_under(root: Path, kind: str) -> list[Bottle]:
    if (root / "drive_c").is_dir():
        return [Bottle(root, kind)]
    out = []
    try:
        children = sorted(root.iterdir())
    except OSError:
        return []
    for child in children:
        if (child / "drive_c").is_dir():
            out.append(Bottle(child, kind))
        elif (child / "pfx" / "drive_c").is_dir():  # Heroic keeps the prefix inside the game's folder
            out.append(Bottle(child / "pfx", kind))
    return out


def _whisky_roots() -> list[tuple[Path, str]]:
    """Bottles Whisky keeps outside its own folder (another drive, say) are listed in BottleVM.plist."""
    out = []
    for app in WHISKY_IDS:
        paths = _read_plist(CONTAINERS / app / "BottleVM.plist").get("paths")
        for entry in paths if isinstance(paths, list) else []:
            path = _file_url(entry.get("relative") if isinstance(entry, dict) else entry)
            if path:
                out.append((path, "Whisky"))
    return out


def _heroic_prefix(app_name: str) -> Path | None:
    """The prefix Heroic set up for one game, from GamesConfig/<app name>.json."""
    data = _read_json(HEROIC_DIR / "GamesConfig" / f"{app_name}.json")
    entry = data.get(app_name) if isinstance(data, dict) else None
    value = entry.get("winePrefix") if isinstance(entry, dict) else None
    return Path(value) if isinstance(value, str) and value else None


def _heroic_roots() -> list[tuple[Path, str]]:
    """Heroic writes where its prefixes go into its own config; the user can move them anywhere."""
    out = []
    config = _read_json(HEROIC_DIR / "config.json")
    defaults = config.get("defaultSettings") if isinstance(config, dict) else None
    for key in ("defaultWinePrefix", "winePrefix"):
        value = defaults.get(key) if isinstance(defaults, dict) else None
        if isinstance(value, str) and value:
            out.append((Path(value), "Heroic"))
    try:
        configs = sorted((HEROIC_DIR / "GamesConfig").glob("*.json"))
    except OSError:
        configs = []
    for path in configs:
        prefix = _heroic_prefix(path.stem)
        if prefix:
            out.append((prefix, "Heroic"))
    return out


def _windows_game(entry: dict) -> bool:
    return str(entry.get("platform") or "windows").lower() == "windows"


def _heroic_library() -> list[tuple[str, Path]]:
    """(app name, folder) for each Windows game Heroic installed: added by hand, from GOG, and from Epic."""
    out = []
    side = _read_json(HEROIC_DIR / "sideload_apps" / "library.json")
    for game in side.get("games", []) if isinstance(side, dict) else []:
        if not isinstance(game, dict):
            continue
        install = game.get("install") if isinstance(game.get("install"), dict) else {}
        if not _windows_game(install):
            continue
        exe = install.get("executable")
        folder = Path(exe).parent if isinstance(exe, str) and exe else None
        if folder is None and isinstance(game.get("folder_name"), str) and game["folder_name"]:
            folder = Path(game["folder_name"])
        if folder:
            out.append((str(game.get("app_name") or ""), folder))
    gog = _read_json(HEROIC_DIR / "gog_store" / "installed.json")
    for game in gog.get("installed", []) if isinstance(gog, dict) else []:
        if isinstance(game, dict) and _windows_game(game) and isinstance(game.get("install_path"), str):
            out.append((str(game.get("appName") or ""), Path(game["install_path"])))
    epic = _read_json(HEROIC_DIR / "legendaryConfig" / "legendary" / "installed.json")
    for app, game in epic.items() if isinstance(epic, dict) else []:
        if isinstance(game, dict) and _windows_game(game) and isinstance(game.get("install_path"), str):
            out.append((app, Path(game["install_path"])))
    return [(app, folder) for app, folder in out if folder.is_absolute()]


def heroic_installs() -> list[tuple[Path, Path | None]]:
    """Every game folder Heroic knows of, with the prefix it runs in. These live outside any drive_c."""
    return [(folder, _heroic_prefix(app) if app else None) for app, folder in _heroic_library()]


def _roots() -> list[tuple[Path, str]]:
    roots = list(BOTTLE_ROOTS)
    for find in (_whisky_roots, _heroic_roots):
        try:
            roots += find()
        except Exception as exc:  # a launcher's config must never stop the search
            log.warning("%s failed: %s", find.__name__, exc)
    env = os.environ.get("WINEPREFIX")
    if env:
        roots.insert(0, (Path(env), "WINEPREFIX"))
    return roots


def bottles() -> list[Bottle]:
    """Every Wine prefix we can find, plus $WINEPREFIX when it is set."""
    out: list[Bottle] = []
    seen = set()
    for root, kind in _roots():
        try:
            if not root.is_dir():
                continue
            found = _prefixes_under(root, kind)
        except OSError as exc:
            log.warning("cannot scan %s: %s", root, exc)
            continue
        for bottle in found:
            key = str(bottle.prefix.resolve())
            if key not in seen:
                seen.add(key)
                out.append(bottle)
    return out


def _kind_of(prefix: Path) -> str:
    return next((k for root, k in _roots() if root == prefix or root in prefix.parents), "Wine")


def _related(a: Path, b: Path) -> bool:
    return a == b or a in b.parents or b in a.parents


def _has_played(bottle: Bottle) -> bool:
    return any((d / "The Witcher 3").is_dir() for d in bottle.documents_dirs())


def bottle_of(path: Path | str) -> Bottle | None:
    """The bottle a game folder belongs to: either under its drive_c, or the one its launcher runs it in.

    A game outside drive_c is reachable from every bottle (Wine maps Z: to /), so a launcher's own record
    wins; failing that, the bottle whose drive maps the folder most closely, then one the game has run in."""
    target = Path(path).resolve()
    for parent in [target, *target.parents]:
        if parent.name == "drive_c" and (parent.parent / "dosdevices").is_dir():
            return Bottle(parent.parent, _kind_of(parent.parent))
    found = bottles()
    for bottle in found:  # Whisky pins the exe the user ran
        if any(_related(target, p.resolve()) for p in bottle.pinned_programs()):
            return bottle
    for folder, prefix in heroic_installs():
        if prefix and _related(target, folder.resolve()):
            match = next((b for b in found if b.prefix.resolve() == prefix.resolve()), None)
            if match:
                return match
    best, best_score = None, None
    for bottle in found:
        depth = max((len(d.parts) for d in bottle.drives() if d == target or d in target.parents), default=0)
        if not depth:
            continue
        score = (depth, _has_played(bottle))
        if best_score is None or score > best_score:
            best, best_score = bottle, score
    return best
