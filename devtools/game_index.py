"""Where the game uses each string: key names, journal sections and entity templates.

String keys are stored hashed in .w3strings; hashing every word found in the game's XML, CSV,
scripts and resources recovers most of them (map pins hold a tag that gets "map_location_"
in front). Journal resources and entity templates refer to strings by id instead.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.bundle import iter_bundle
from core.paths import cache_dir
from core.w3strings import W3Strings, hash_key

INDEX_VERSION = 1
# buffers, movies and bumpers are many GB of meshes, videos and sounds without string references
MAX_BUNDLE = 3_000_000_000
MAX_FILE = 50_000_000
TEXT_FILES = (".xml", ".csv")
RESOURCE_FILES = (".w2ent", ".w2scene", ".w2phase", ".w2cutscene", ".w2comm", ".w2quest", ".journal", ".reddlc")
PIN_FILES = (".w2em", ".w2qm")
PIN_PREFIXES = ("", "map_location_")
WORD = re.compile(rb"[A-Za-z][A-Za-z0-9_\-]{2,80}")
# keys written out in XML and CSV may contain spaces ("mysterious elf")
PHRASE = re.compile(rb"[A-Za-z][A-Za-z0-9_\- ]{2,80}")
# a LocalizedString property: size 8 followed by the string id
LOCALIZED = re.compile(rb"\x08\x00\x00\x00(....)", re.S)
MAX_ENTITY_PATHS = 10


@dataclass
class GameIndex:
    # key hash -> (key name, where it was seen: file name for XML / CSV, extension for resources, "ws")
    key_names: dict[int, tuple[str, list[str]]] = field(default_factory=dict)
    # string id -> journal sections referring to it (characters, bestiary, places, quests, ...)
    journal: dict[int, list[str]] = field(default_factory=dict)
    # string id -> entity templates using it as a display name
    entities: dict[int, list[str]] = field(default_factory=dict)


def _bundles(game_path: Path) -> list[Path]:
    root = game_path / "content"
    return sorted(p for p in root.rglob("*.bundle") if p.stat().st_size <= MAX_BUNDLE)


def _scripts(game_path: Path) -> list[Path]:
    return sorted((game_path / "content").rglob("*.ws"))


def _stamp(game_path: Path, english: W3Strings) -> list:
    files = [(str(p.relative_to(game_path)), p.stat().st_size, p.stat().st_mtime_ns)
             for p in _bundles(game_path)]
    scripts = _scripts(game_path)
    newest = max((p.stat().st_mtime_ns for p in scripts), default=0)
    return [INDEX_VERSION, english.version, len(english.strings), len(scripts), newest, files]


def _journal_section(path: str) -> str | None:
    parts = path.lower().split("\\")
    if "journal" not in parts[:-1]:
        return None
    i = parts.index("journal")
    return parts[i + 1] if i + 1 < len(parts) - 1 else None


def _source(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return os.path.basename(path).lower() if ext in TEXT_FILES else ext


def scan(game_path: Path, english: W3Strings, log=print) -> GameIndex:
    keys = set(english.keys.values())
    # only short strings can be names; this keeps random numbers in binary data from matching
    ids = {sid for sid, text in english.strings.items()
           if text.strip() and len(text) <= 80 and "<" not in text and "\n" not in text}
    found: dict[int, tuple[str, set[str]]] = {}
    journal: dict[int, set[str]] = {}
    entities: dict[int, list[str]] = {}

    def add_words(data: bytes, source: str, patterns=(WORD,), prefixes=("",)) -> None:
        words = set()
        for pat in patterns:
            words.update(w.strip().lower() for w in pat.findall(data))
        for w in words:
            try:
                text = w.decode("ascii")
            except UnicodeDecodeError:
                continue
            for prefix in prefixes:
                h = hash_key(prefix + text)
                if h in keys:
                    entry = found.setdefault(h, (prefix + text, set()))
                    entry[1].add(source)

    for path in _scripts(game_path):
        add_words(path.read_bytes(), "ws")
    wanted = TEXT_FILES + RESOURCE_FILES + PIN_FILES
    for bundle in _bundles(game_path):
        log(f"scan {bundle.name}")
        files = iter_bundle(bundle, lambda n, size: size <= MAX_FILE and n.lower().endswith(wanted))
        for f in files:
            name = f.path.lower()
            ext = os.path.splitext(name)[1]
            if ext in TEXT_FILES:
                add_words(f.data, _source(name), (WORD, PHRASE))
            elif ext in PIN_FILES:
                add_words(f.data, ext, prefixes=PIN_PREFIXES)
            else:
                add_words(f.data, ext)
            if ext == ".journal":
                section = _journal_section(name)
                if section:
                    for m in LOCALIZED.finditer(f.data):
                        sid = int.from_bytes(m.group(1), "little")
                        if sid in ids:
                            journal.setdefault(sid, set()).add(section)
            elif ext == ".w2ent":
                for m in LOCALIZED.finditer(f.data):
                    sid = int.from_bytes(m.group(1), "little")
                    if sid in ids:
                        paths = entities.setdefault(sid, [])
                        if f.path not in paths and len(paths) < MAX_ENTITY_PATHS:
                            paths.append(f.path)
    return GameIndex({h: (n, sorted(s)) for h, (n, s) in found.items()},
                     {sid: sorted(s) for sid, s in journal.items()}, entities)


def _cache_path() -> Path:
    return cache_dir() / "names_index.json.gz"


def build_index(game_path, english: W3Strings, log=print) -> GameIndex:
    """The index for this game install, from the cache when the game files have not changed."""
    game_path = Path(game_path)
    stamp = _stamp(game_path, english)
    path = _cache_path()
    if path.exists():
        try:
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                payload = json.load(fh)
            if payload.get("stamp") == json.loads(json.dumps(stamp)):
                return GameIndex({int(k): (v[0], v[1]) for k, v in payload["keys"].items()},
                                 {int(k): v for k, v in payload["journal"].items()},
                                 {int(k): v for k, v in payload["entities"].items()})
        except (OSError, ValueError, KeyError) as exc:
            log(f"names index cache unreadable: {exc}")
    index = scan(game_path, english, log)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"stamp": stamp,
                   "keys": {str(k): [n, s] for k, (n, s) in index.key_names.items()},
                   "journal": {str(k): v for k, v in index.journal.items()},
                   "entities": {str(k): v for k, v in index.entities.items()}}, fh, ensure_ascii=False)
    return index


if __name__ == "__main__":
    import time

    from core.game_detect import identify
    from core.options import load_options
    from core.text_builder import _load_merged

    game = identify(load_options().game_path)
    t0 = time.time()
    idx = build_index(game.path, _load_merged(game, "en", []))
    print(f"{len(idx.key_names):,} key names, {len(idx.journal):,} journal ids, "
          f"{len(idx.entities):,} entity ids in {time.time() - t0:.0f}s")
