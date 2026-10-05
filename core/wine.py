"""Wine prefixes on macOS. The game has no Mac build, so a Mac player's copy lives inside a bottle.

A prefix is a folder holding drive_c/ next to dosdevices/, where each drive letter is a symlink, and
system.reg / user.reg hold the same registry the Windows build reads.
"""
from __future__ import annotations

import functools
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

HOME = Path.home()
# each entry holds one prefix, or a folder of them; Heroic keeps its prefix one level down in pfx/
BOTTLE_ROOTS = (
    (HOME / "Library/Application Support/CrossOver/Bottles", "CrossOver"),
    (HOME / "Library/Containers/com.isaacmarovitz.Whisky/Bottles", "Whisky"),
    (HOME / "Library/Application Support/Whisky/Bottles", "Whisky"),
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
        return f"{self.kind}: {self.prefix.name}"

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
        for user in sorted(users.iterdir()):
            docs = user / "Documents"
            if docs.is_dir():
                out.append(docs)
        return out


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


def bottles() -> list[Bottle]:
    """Every Wine prefix we can find, plus $WINEPREFIX when it is set."""
    out: list[Bottle] = []
    seen = set()
    roots = list(BOTTLE_ROOTS)
    env = os.environ.get("WINEPREFIX")
    if env:
        roots.insert(0, (Path(env), "WINEPREFIX"))
    for root, kind in roots:
        try:
            if not root.is_dir():
                continue
            found = _prefixes_under(root, kind)
        except OSError as exc:
            log.warning("cannot scan %s: %s", root, exc)
            continue
        for bottle in found:
            key = str(bottle.prefix)
            if key not in seen:
                seen.add(key)
                out.append(bottle)
    return out


def _kind_of(prefix: Path) -> str:
    return next((k for root, k in BOTTLE_ROOTS if root == prefix or root in prefix.parents), "Wine")


def bottle_of(path: Path | str) -> Bottle | None:
    """The bottle a game folder belongs to: either under its drive_c, or under one of its mapped drives."""
    target = Path(path).resolve()
    for parent in [target, *target.parents]:
        if parent.name == "drive_c" and (parent.parent / "dosdevices").is_dir():
            return Bottle(parent.parent, _kind_of(parent.parent))
    for bottle in bottles():  # a game on D: lives outside drive_c entirely
        for drive in bottle.drives():
            if drive == target or drive in target.parents:
                return bottle
    return None
