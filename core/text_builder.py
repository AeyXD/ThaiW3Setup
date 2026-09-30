"""Merge the Thai translation into the game's strings and produce .w3strings files."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .game_detect import GameInfo
from .options import InstallOptions, MODE_DOUBLE, SLOT_TR
from .progress import ProgressFn, noop
from .sheet import normalize
from .w3strings import VERSION_UTF16, VERSION_UTF8, W3Strings, W3StringsError

log = logging.getLogger(__name__)

LANGUAGE_NAME_ID = 1084967  # "Turkish" entry in the language list
THAI_LABEL = "ไทย (Thai)"


@dataclass
class TextResult:
    files: dict[str, bytes]  # file name -> content
    total: int
    translated: int
    skipped: list[Path] = field(default_factory=list)

    @property
    def percent(self) -> float:
        return 100.0 * self.translated / self.total if self.total else 0.0


def _load_merged(game: GameInfo, language: str, skipped: list[Path]) -> W3Strings | None:
    merged = None
    for path in game.strings_files(language):
        try:
            w = W3Strings.load(path, language)
        except (W3StringsError, OSError, ValueError) as exc:
            log.warning("skip unreadable %s: %s", path, exc)
            skipped.append(path)
            continue
        if merged is None:
            merged = w
        else:
            merged.strings.update(w.strings)
            merged.keys.update(w.keys)
            merged.version = max(merged.version, w.version)
    return merged


def combine(thai: str, english: str, thai_first: bool) -> str:
    if not english.strip() or english.strip() == thai.strip():
        return thai
    first, second = (thai, english) if thai_first else (english, thai)
    first = first.replace("  [", " [")
    return f"{first}  [{second}]"


def _thai_for(sid: int, en_text: str, thai: dict[int, str], by_text: dict[str, str] | None,
              overrides: dict[int, str]) -> str | None:
    th = overrides.get(sid) or thai.get(sid)
    if not th and by_text and en_text.strip():
        th = by_text.get(normalize(en_text))
    return th


def untranslated(game: GameInfo, thai: dict[int, str], by_text: dict[str, str] | None = None,
                 overrides: dict[int, str] | None = None) -> dict[int, str]:
    """English strings (id -> text) that build_texts would leave untranslated, ignoring empty ones."""
    english = _load_merged(game, "en", [])
    if english is None:
        raise RuntimeError("en.w3strings not found")
    overrides = overrides or {}
    return {sid: text for sid, text in english.strings.items()
            if text.strip() and not _thai_for(sid, text, thai, by_text, overrides)}


def build_texts(game: GameInfo, thai: dict[int, str], opts: InstallOptions,
                progress: ProgressFn = noop, by_text: dict[str, str] | None = None,
                overrides: dict[int, str] | None = None) -> TextResult:
    """thai is keyed by string id; by_text (English -> Thai) fills ids thai does not cover;
    overrides (custom sheets, keyed by id) replace both."""
    overrides = overrides or {}
    progress(0.0, "กำลังอ่านไฟล์ข้อความของเกม...")
    skipped: list[Path] = []
    english = _load_merged(game, "en", skipped)
    if english is None:
        detail = "\n".join(str(p) for p in skipped)
        raise RuntimeError("อ่านไฟล์ en.w3strings ของเกมไม่ได้ ไฟล์อาจเสียหรือถูกโปรแกรมอื่นแก้ไข\n"
                           "ให้ใช้ Verify integrity of game files ใน Steam/GOG แล้วติดตั้งใหม่"
                           + (f"\n\n{detail}" if detail else ""))
    slot = english if opts.slot == "en" else _load_merged(game, opts.slot, skipped)
    progress(0.4, "กำลังรวมคำแปล...")

    version = VERSION_UTF8 if english.version >= VERSION_UTF8 else VERSION_UTF16
    keyed = set(english.keys)
    if slot is not None:
        keyed |= set(slot.keys)

    ids = set(english.strings)
    if slot is not None:
        ids |= set(slot.strings)

    out = W3Strings(language=opts.slot, version=version)
    double = opts.mode == MODE_DOUBLE
    translated = 0
    for sid in ids:
        en_text = english.strings.get(sid)
        if en_text is None:
            en_text = slot.strings.get(sid, "") if slot is not None else ""
        th = _thai_for(sid, en_text, thai, by_text, overrides)
        if th and sid in english.strings:
            translated += 1
        if th:
            out.strings[sid] = combine(th, en_text, opts.thai_first) if double and sid not in keyed else th
        else:
            out.strings[sid] = en_text
    out.keys.update(english.keys)
    if slot is not None and slot is not english:
        out.keys.update(slot.keys)

    files = {}
    if opts.slot == SLOT_TR:
        out.strings[LANGUAGE_NAME_ID] = THAI_LABEL
        label = W3Strings(language="en", version=version,
                          strings={LANGUAGE_NAME_ID: THAI_LABEL},
                          keys={LANGUAGE_NAME_ID: english.keys[LANGUAGE_NAME_ID]} if LANGUAGE_NAME_ID in english.keys else {})
        files["en.w3strings"] = label.build()

    progress(0.7, "กำลังสร้างไฟล์ข้อความ...")
    files[f"{opts.slot}.w3strings"] = out.build()
    progress(1.0, "สร้างไฟล์ข้อความภาษาไทยเสร็จแล้ว")
    return TextResult(files, len(english.strings), translated, skipped)
