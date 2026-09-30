"""Install / uninstall / status for the Thai mod. Only touches mods/modThai*."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from . import __version__
from .assets import font_files, storybook_files, write_mod_content
from .custom import merged_overrides
from .game_detect import GameInfo, identify
from .options import InstallOptions
from .progress import ProgressFn, noop, scaled
from .script_patcher import MODULES_REL, PatchError, ScriptOptions, build_scripts
from .sheet import get_translations
from .text_builder import build_texts
from .w3strings import W3Strings

log = logging.getLogger(__name__)

MOD_TEXT = "modThaiText"
MOD_FONT = "modThaiFont"
MOD_STORY = "modThaiStoryBook"
MOD_SCRIPT = "modThaiDoubleSub"
OUR_MODS = (MOD_TEXT, MOD_FONT, MOD_STORY, MOD_SCRIPT)
MANIFEST = "thai_manifest.json"
LEGACY_PATTERN = re.compile(r"^modkuntoonw3thai", re.IGNORECASE)
THAI_CHARS = re.compile("[\u0e00-\u0e7f]")

ConfirmFn = Callable[[str], bool]


@dataclass
class InstallReport:
    translated: int = 0
    total: int = 0
    source: str = ""
    fetched: str = ""
    custom: int = 0
    warnings: list[str] = field(default_factory=list)
    mods: list[str] = field(default_factory=list)

    @property
    def percent(self) -> float:
        return 100.0 * self.translated / self.total if self.total else 0.0


@dataclass
class Status:
    installed: bool
    version: str = ""
    options: dict | None = None
    installed_at: str = ""
    percent: float = 0.0
    mods: list[str] = field(default_factory=list)
    legacy_mods: list[str] = field(default_factory=list)


def legacy_mods(game: GameInfo) -> list[Path]:
    if not game.mods_dir.is_dir():
        return []
    return [p for p in game.mods_dir.iterdir() if p.is_dir() and LEGACY_PATTERN.match(p.name)]


def base_strings_modified(game: GameInfo) -> bool:
    """True if w3tu overwrote the game's own en.w3strings (only possible on 4.x)."""
    files = game.strings_files("en")
    if not files:
        return False
    try:
        w = W3Strings.load(files[0], "en")
    except Exception:
        return False
    sample = list(w.strings.values())[:3000]
    return sum(1 for s in sample if THAI_CHARS.search(s)) > 100


def status(game: GameInfo) -> Status:
    manifest = game.mods_dir / MOD_TEXT / MANIFEST
    legacy = [p.name for p in legacy_mods(game)]
    if not manifest.exists():
        present = [m for m in OUR_MODS if (game.mods_dir / m).exists()]
        return Status(bool(present), mods=present, legacy_mods=legacy)
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Status(True, mods=list(OUR_MODS), legacy_mods=legacy)
    return Status(True, data.get("version", ""), data.get("options"), data.get("installed_at", ""),
                  float(data.get("percent", 0)), data.get("mods", []), legacy)


def _check_writable(mods_dir: Path) -> None:
    mods_dir.mkdir(parents=True, exist_ok=True)
    probe = mods_dir / ".thai_write_test"
    probe.write_bytes(b"ok")
    probe.unlink()


def _remove_our_mods(game: GameInfo) -> None:
    for name in OUR_MODS:
        target = game.mods_dir / name
        if target.exists():
            shutil.rmtree(target)


def install(opts: InstallOptions, progress: ProgressFn = noop, confirm: ConfirmFn = lambda _m: True,
            force_download: bool = False) -> InstallReport:
    opts.validate()
    game = identify(opts.game_path)
    if not game.supported:
        raise RuntimeError(f"ไม่รองรับเกมในโฟลเดอร์นี้: {game.label}")
    report = InstallReport()

    try:
        _check_writable(game.mods_dir)
    except PermissionError as exc:
        raise PermissionError(f"ไม่มีสิทธิ์เขียนไฟล์ลงโฟลเดอร์ {game.mods_dir}") from exc

    old = legacy_mods(game)
    if old:
        names = ", ".join(p.name for p in old)
        if confirm(f"พบ mod ภาษาไทยตัวเก่าของ w3tu ({names}) ซึ่งจะทำงานชนกับตัวใหม่\nต้องการลบออกหรือไม่?"):
            for p in old:
                shutil.rmtree(p)
        else:
            report.warnings.append(f"ยังมี mod ไทยตัวเก่า ({names}) อยู่ อาจทำให้แสดงผลผิดพลาด")
    if base_strings_modified(game):
        report.warnings.append("ไฟล์ข้อความของตัวเกมถูกโปรแกรมเก่าแก้ไขไว้ แนะนำให้ใช้ Verify integrity of game files ใน Steam/GOG")

    tr = get_translations(force_download=force_download, progress=scaled(progress, 0.0, 0.38))
    report.source, report.fetched = tr.source, tr.age_text
    overrides = merged_overrides(opts.custom_sheets, force_download, scaled(progress, 0.38, 0.45))
    report.custom = len(overrides)

    text = build_texts(game, tr.thai, opts, scaled(progress, 0.45, 0.75), by_text=tr.by_text,
                       overrides=overrides)
    report.translated, report.total = text.translated, text.total
    if text.skipped:
        names = ", ".join(str(p.relative_to(game.path)) for p in text.skipped)
        report.warnings.append(f"ข้ามไฟล์ข้อความของเกมที่อ่านไม่ได้ ({names}) ข้อความบางส่วนอาจไม่แปล"
                               " แนะนำให้ใช้ Verify integrity of game files ใน Steam/GOG แล้วติดตั้งใหม่")

    progress(0.78, "เตรียมฟอนต์และซับ Storybook...")
    staging = Path(tempfile.mkdtemp(prefix="thaiw3_"))
    try:
        (staging / MOD_TEXT / "content").mkdir(parents=True)
        for name, data in text.files.items():
            (staging / MOD_TEXT / "content" / name).write_bytes(data)
        report.mods.append(MOD_TEXT)

        write_mod_content(staging / MOD_FONT / "content", font_files(opts.font))
        report.mods.append(MOD_FONT)

        if opts.storybook:
            write_mod_content(staging / MOD_STORY / "content", storybook_files(opts.slot))
            report.mods.append(MOD_STORY)

        if opts.subtitle_style:
            progress(0.85, "ปรับ script สีและขนาดซับ...")
            try:
                scripts = build_scripts(game.script_modules, ScriptOptions(
                    opts.color1, opts.color2, opts.size1, opts.size2, opts.speaker_colors,
                    opts.sub_x, opts.sub_y, opts.sub_width, opts.dialog_x, opts.dialog_y,
                    opts.choice_x, opts.choice_y, opts.choice_scale))
                target = staging / MOD_SCRIPT / "content" / MODULES_REL
                target.mkdir(parents=True)
                for name, data in scripts.items():
                    (target / name).write_bytes(data)
                report.mods.append(MOD_SCRIPT)
            except PatchError as exc:
                log.warning("script patch skipped: %s", exc)
                report.warnings.append("script ของเกมเวอร์ชันนี้ไม่ตรงกับที่รองรับ จึงข้ามการปรับสี/ขนาดซับ"
                                       " (ข้อความภาษาไทยยังใช้งานได้ปกติ)")

        manifest = {
            "version": __version__,
            "installed_at": time.strftime("%Y-%m-%d %H:%M"),
            "edition": game.edition,
            "options": asdict(opts),
            "mods": report.mods,
            "translated": report.translated,
            "total": report.total,
            "percent": round(report.percent, 2),
            "translation_source": report.source,
        }
        (staging / MOD_TEXT / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        progress(0.93, "คัดลอกไฟล์ลงโฟลเดอร์ mods...")
        _remove_our_mods(game)
        for name in report.mods:
            shutil.copytree(staging / name, game.mods_dir / name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    progress(1.0, "ติดตั้งเสร็จแล้ว")
    return report


def uninstall(game_path: str | os.PathLike) -> list[str]:
    game = identify(game_path)
    removed = [n for n in OUR_MODS if (game.mods_dir / n).exists()]
    _remove_our_mods(game)
    return removed
