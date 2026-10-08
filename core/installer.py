"""Install / export / uninstall / status for the Thai mod. Only touches mods/modThai*."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Callable

from . import __version__
from . import mods_settings
from .assets import font_files, storybook_files, write_mod_content
from .bundle import BundleError
from .compat import (COMPAT_MODS, MISSING, PatchStatus, game_parts, installed_patches, open_sources, patch_files,
                     patch_info, patch_readme, patch_status, patched_paths, write_patch_info)
from .custom import merged_overrides
from .game_detect import GameInfo, identify
from .panel_layout import LayoutError, panel_files
from .logo import LogoError, logo_files
from .options import SLOT_EN, InstallOptions
from .progress import ProgressFn, noop, scaled
from .script_patcher import MODULES_REL, SCRIPT_FILES, PatchError, ScriptOptions, build_scripts
from .sheet import get_translations
from .text_builder import build_texts, coverage
from .w3strings import W3Strings

log = logging.getLogger(__name__)

MOD_TEXT = "modThaiText"
MOD_FONT = "modThaiFont"
MOD_STORY = "modThaiStoryBook"
MOD_SCRIPT = "modThaiDoubleSub"
MOD_LOGO = "modThaiLogo"
OUR_MODS = (MOD_TEXT, MOD_FONT, MOD_STORY, MOD_SCRIPT, MOD_LOGO)
# patch folders are only ours to remove when our manifest lists them; the Mod Manager may own them instead
PATCH_MODS = tuple(m.patch for m in COMPAT_MODS.values())
MANIFEST = "thai_manifest.json"
LEGACY_PATTERN = re.compile(r"^modkuntoonw3thai", re.IGNORECASE)
# ThaiLanguage Remastered 5.0 on Nexus ships modThaiLanguage plus its own modThaiFont (same name as ours)
FOREIGN_THAI_PATTERN = re.compile(r"^modThaiLanguage$", re.IGNORECASE)
DISABLED_DIR = "mods_disabled"
EXPORT_DIR = "ThaiW3_mods"
EXPORT_ZIP = "ThaiW3_mods.zip"
EXPORT_README = "วิธีติดตั้ง.txt"
PATCH_README = "README_TH.txt"
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
    output: str = ""
    compat: list[str] = field(default_factory=list)

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
    foreign_mods: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    compat: list[PatchStatus] = field(default_factory=list)


def legacy_mods(game: GameInfo) -> list[Path]:
    if not game.mods_dir.is_dir():
        return []
    return [p for p in game.mods_dir.iterdir() if p.is_dir() and LEGACY_PATTERN.match(p.name)]


def _other_mods(game: GameInfo) -> list[Path]:
    if not game.mods_dir.is_dir():
        return []
    ours = {m.lower() for m in OUR_MODS + PATCH_MODS}
    return [p for p in sorted(game.mods_dir.iterdir())
            if p.is_dir() and p.name.lower() not in ours and not LEGACY_PATTERN.match(p.name)]


def strings_have_thai(path: Path, language: str) -> bool:
    try:
        sample = list(W3Strings.load(path, language).strings.values())[:3000]
    except Exception:
        return False
    return sum(1 for s in sample if THAI_CHARS.search(s)) > 100


def foreign_thai_mods(game: GameInfo, deep: bool = False) -> list[Path]:
    """Thai mods from other sources; their tr.w3strings sorts before modThaiText and wins.

    deep also reads every other mod's .w3strings (seconds per file), so it is for install time only.
    """
    return [p for p in _other_mods(game) if FOREIGN_THAI_PATTERN.match(p.name)
            or (deep and any(strings_have_thai(f, f.stem.lower()) for f in p.rglob("*.w3strings")))]


def script_overlaps(game: GameInfo) -> list[str]:
    """Other mods replacing the HUD scripts modThaiDoubleSub patches; the script compiler rejects duplicates."""
    names = {n.lower() for n in SCRIPT_FILES}
    out = []
    for mod in _other_mods(game):
        hits = sorted({f.name for f in mod.rglob("*.ws") if f.name.lower() in names})
        if hits:
            out.append(f"{mod.name} ({', '.join(hits)})")
    return out


def disable_mods(game: GameInfo, mods: list[Path]) -> Path:
    """Move mods out of mods/ so the game stops loading them; the user can move them back."""
    target = game.path / DISABLED_DIR
    target.mkdir(exist_ok=True)
    for p in mods:
        dest = target / p.name
        if dest.exists():
            dest = target / f"{p.name}_{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.move(str(p), str(dest))
        log.info("moved %s to %s", p, dest)
    return target


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _file_hashes(root: Path, mods: list[str]) -> dict[str, str]:
    return {f.relative_to(root).as_posix(): _sha1(f)
            for name in mods for f in sorted((root / name).rglob("*")) if f.is_file() and f.name != MANIFEST}


def modified_files(game: GameInfo, hashes: dict[str, str]) -> list[str]:
    """Files of our mods that changed or vanished since install, e.g. another modThaiFont copied over ours."""
    out = []
    for rel, digest in hashes.items():
        try:
            if _sha1(game.mods_dir / rel) != digest:
                out.append(rel)
        except OSError:
            out.append(rel)
    return out


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


def _manifest(game: GameInfo) -> dict | None:
    try:
        return json.loads((game.mods_dir / MOD_TEXT / MANIFEST).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {}


def _our_folders(game: GameInfo) -> list[str]:
    """Our mod folders plus the patch folders our last install wrote."""
    listed = (_manifest(game) or {}).get("mods") or []
    return list(OUR_MODS) + [m for m in PATCH_MODS if m in listed]


def compat_status(game: GameInfo, font: str | None = None) -> list[PatchStatus]:
    """Every supported UI mod that is in the game or has a patch there."""
    settings = mods_settings.read(game.path)
    out = []
    for mod in COMPAT_MODS.values():
        st = patch_status(game.mods_dir, mod, settings, font, (MOD_FONT, MOD_LOGO))
        if st.state != MISSING:
            out.append(st)
    return out


def status(game: GameInfo) -> Status:
    legacy = [p.name for p in legacy_mods(game)]
    foreign = [p.name for p in foreign_thai_mods(game)]
    data = _manifest(game)
    font = ((data or {}).get("options") or {}).get("font")
    compat = compat_status(game, font)
    if data is None:
        present = [m for m in OUR_MODS if (game.mods_dir / m).exists()]
        return Status(bool(present), mods=present, legacy_mods=legacy, foreign_mods=foreign, compat=compat)
    if not data:
        return Status(True, mods=list(OUR_MODS), legacy_mods=legacy, foreign_mods=foreign, compat=compat)
    return Status(True, data.get("version", ""), data.get("options"), data.get("installed_at", ""),
                  float(data.get("percent", 0)), data.get("mods", []), legacy, foreign,
                  modified_files(game, data.get("files") or {}), compat)


def _check_writable(mods_dir: Path) -> None:
    mods_dir.mkdir(parents=True, exist_ok=True)
    probe = mods_dir / ".thai_write_test"
    probe.write_bytes(b"ok")
    probe.unlink()


def _check_not_in_use(game: GameInfo, names: list[str]) -> None:
    """Fail before deleting anything when the running game still holds one of our files."""
    for name in names:
        for path in (game.mods_dir / name).rglob("*"):
            if not path.is_file():
                continue
            try:
                with open(path, "ab"):
                    pass
            except PermissionError as exc:
                raise RuntimeError(f"ไฟล์ {path.name} ใน {name} ถูกโปรแกรมอื่นเปิดอยู่ (เช่นตัวเกม)\n"
                                   "ให้ปิดเกมก่อนแล้วกดติดตั้งอีกครั้ง") from exc


def _remove_our_mods(game: GameInfo, also: list[str] = ()) -> None:
    """Remove our folders, and also the given ones (patches about to be rewritten)."""
    names = list(dict.fromkeys(_our_folders(game) + list(also)))
    _check_not_in_use(game, names)
    for name in names:
        target = game.mods_dir / name
        if target.exists():
            shutil.rmtree(target)


def _supported_game(opts: InstallOptions) -> GameInfo:
    opts.validate()
    game = identify(opts.game_path)
    if not game.supported:
        raise RuntimeError(f"ไม่รองรับเกมในโฟลเดอร์นี้: {game.label}")
    log.info("game %s version %s", game.path, game.version or "?")
    if game.stale_content:
        log.warning("leftover 4.x folders: %s", ", ".join(game.stale_content))
    return game


def install(opts: InstallOptions, progress: ProgressFn = noop, confirm: ConfirmFn = lambda _m: True,
            force_download: bool = False) -> InstallReport:
    game = _supported_game(opts)
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
    progress(0.0, "ตรวจหา mod ภาษาไทยตัวอื่น...")
    foreign = foreign_thai_mods(game, deep=True)
    if foreign:
        names = ", ".join(p.name for p in foreign)
        if confirm(f"พบ mod ภาษาไทยจากที่อื่น ({names}) เช่น ThaiLanguage Remastered จาก Nexus\n"
                   "ซึ่งจะทับข้อความและซับของตัวนี้ ทำให้ภาษาไทยแสดงเพี้ยน\n"
                   f"ต้องการย้ายออกไปไว้ที่โฟลเดอร์ {DISABLED_DIR} ในโฟลเดอร์เกมหรือไม่? (ย้ายกลับเองได้)"):
            target = disable_mods(game, foreign)
            report.warnings.append(f"ย้าย mod ไทยจากที่อื่น ({names}) ไปไว้ที่ {target} แล้ว")
        else:
            report.warnings.append(f"ยังมี mod ไทยจากที่อื่น ({names}) อยู่ในโฟลเดอร์ mods ภาษาไทยจะแสดงเพี้ยน")
    opts = replace(opts, compat=_confirm_compat(game, opts, confirm, report))
    report.compat = list(opts.compat)
    staging = Path(tempfile.mkdtemp(prefix="thaiw3_"))
    try:
        _build_mods(game, opts, staging, report, progress, force_download)
        progress(0.93, "คัดลอกไฟล์ลงโฟลเดอร์ mods...")
        _remove_our_mods(game, [m for m in report.mods if m in PATCH_MODS])
        for name in report.mods:
            shutil.copytree(staging / name, game.mods_dir / name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    log.info("installed %s to %s (%.2f%%)", ", ".join(report.mods), game.mods_dir, report.percent)
    progress(1.0, "ติดตั้งเสร็จแล้ว")
    return report


def _compat_source_ready(game: GameInfo, key: str, opts: InstallOptions,
                         settings: dict | None = None) -> bool:
    """True when the toggled UI mod is in the game's mods folder or a zip/folder was chosen."""
    mod = COMPAT_MODS[key]
    if settings is None:
        settings = mods_settings.read(game.path)
    if game_parts(game.mods_dir, mod, settings):
        return True
    source = opts.compat_sources.get(key)
    return bool(source and Path(source).exists())


def _confirm_compat(game: GameInfo, opts: InstallOptions, confirm: ConfirmFn, report: InstallReport) -> list[str]:
    """The toggled UI mods to patch. Asks only when a foreign patch would be replaced."""
    settings = mods_settings.read(game.path)
    ours = set(_our_folders(game))
    keys = []
    for key in opts.compat:
        mod = COMPAT_MODS[key]
        if not _compat_source_ready(game, key, opts, settings):
            raise RuntimeError(
                f"เปิดแพตช์ {mod.label} ไว้ แต่ยังไม่พบ {mod.label} ในโฟลเดอร์ mods "
                f"และยังไม่ได้เลือกไฟล์ต้นทาง\nให้ติดตั้ง {mod.label} หรือเลือกไฟล์ zip ก่อน"
            )
        others = [p for p in installed_patches(game.mods_dir, mod) if p not in ours]
        if others and not confirm(
            f"มีแพตช์ {mod.label} ติดตั้งไว้แล้ว ({', '.join(others)}) เช่นผ่าน Mod Manager\n"
            "จะติดตั้งแพตช์จากโปรแกรมนี้อีกชุดหรือไม่? (ควรใช้ชุดเดียว)"
        ):
            continue
        keys.append(key)
    return keys


def _require_compat_sources(game: GameInfo, opts: InstallOptions) -> list[str]:
    """Return toggled compat keys, or raise if any toggled mod has no source."""
    settings = mods_settings.read(game.path)
    for key in opts.compat:
        mod = COMPAT_MODS[key]
        if not _compat_source_ready(game, key, opts, settings):
            raise RuntimeError(
                f"เปิดแพตช์ {mod.label} ไว้ แต่ยังไม่พบ {mod.label} ในโฟลเดอร์ mods "
                f"และยังไม่ได้เลือกไฟล์ต้นทาง\nให้ติดตั้ง {mod.label} หรือเลือกไฟล์ zip ก่อน"
            )
    return list(opts.compat)


def _build_patches(game: GameInfo, opts: InstallOptions, staging: Path, report: InstallReport,
                   progress: ProgressFn) -> None:
    settings = mods_settings.read(game.path)
    for i, key in enumerate(opts.compat):
        mod = COMPAT_MODS[key]
        source = opts.compat_sources.get(key)
        part = scaled(progress, i / len(opts.compat), (i + 1) / len(opts.compat))
        part(0.0, f"ทำแพตช์ภาษาไทยสำหรับ {mod.label}...")
        with open_sources(mod, game.mods_dir, source, settings) as sources:
            files, warnings = patch_files(sources, opts.font, opts.thai_logo, part)
            info = patch_info(sources, opts.font, opts.thai_logo)
        write_mod_content(staging / mod.patch / "content", files)
        write_patch_info(staging / mod.patch, info)
        report.mods.append(mod.patch)
        report.warnings += warnings
        if mods_settings.disabled(mod.patch, settings):
            report.warnings.append(f"{mod.patch} ถูกปิดอยู่ใน Mod Manager / mods.settings ให้เปิดก่อนเข้าเกม")
        ahead = mods_settings.loses_to(mod.patch, list(info["sources"]), settings)
        if ahead:
            report.warnings.append(f"ใน mods.settings {', '.join(ahead)} โหลดก่อน {mod.patch} ให้ตั้ง Priority"
                                   f" ของ {mod.patch} ใน Mod Manager ให้เลขน้อยกว่า (เช่น 0)")


def _build_mods(game: GameInfo, opts: InstallOptions, staging: Path, report: InstallReport,
                progress: ProgressFn, force_download: bool) -> None:
    """Write every enabled mod folder and the manifest into staging, filling in report."""
    if base_strings_modified(game):
        report.warnings.append("ไฟล์ข้อความของตัวเกมถูกโปรแกรมเก่าแก้ไขไว้ แนะนำให้ใช้ Verify integrity of game files ใน Steam/GOG")

    tr = get_translations(force_download=force_download, progress=scaled(progress, 0.0, 0.38))
    report.source, report.fetched = tr.source, tr.age_text
    overrides = merged_overrides(opts.custom_sheets, force_download, scaled(progress, 0.38, 0.45))
    report.custom = len(overrides.strings)

    text = build_texts(game, tr.thai, opts, scaled(progress, 0.45, 0.75), by_text=tr.by_text,
                       overrides=overrides)
    report.translated, report.total = text.translated, text.total
    if text.skipped:
        names = ", ".join(str(p.relative_to(game.path)) for p in text.skipped)
        report.warnings.append(f"ข้ามไฟล์ข้อความของเกมที่อ่านไม่ได้ ({names}) ข้อความบางส่วนอาจไม่แปล"
                               " แนะนำให้ใช้ Verify integrity of game files ใน Steam/GOG แล้วติดตั้งใหม่")

    progress(0.78, "เตรียมฟอนต์และซับ Storybook...")
    (staging / MOD_TEXT / "content").mkdir(parents=True)
    for name, data in text.files.items():
        (staging / MOD_TEXT / "content" / name).write_bytes(data)
    report.mods.append(MOD_TEXT)

    try:
        leave = patched_paths(game.mods_dir, mods_settings.read(game.path), set(opts.compat),
                              set(_our_folders(game)))
    except (OSError, BundleError) as exc:
        log.warning("could not list the patched mods' files: %s", exc)
        leave = set()
    if leave:
        log.info("leaving %d files to patched UI mods", len(leave))

    gui_files = font_files(opts.font)
    try:
        gui_files += panel_files(game.content0, scaled(progress, 0.78, 0.8))
    except (LayoutError, BundleError, OSError) as exc:
        log.warning("panel layout skipped: %s", exc)
        report.warnings.append("ไฟล์หน้าภารกิจ/บันทึกของเกมเวอร์ชันนี้ไม่ตรงกับที่รองรับ จึงข้ามการจัดรูปแบบข้อความ"
                               " (ข้อความภาษาไทยยังใช้งานได้ปกติ)")
    gui_files = [f for f in gui_files if f.path not in leave]
    if gui_files:
        write_mod_content(staging / MOD_FONT / "content", gui_files)
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
                opts.choice_x, opts.choice_y, opts.choice_scale,
                show_speaker_dialog=opts.show_speaker_dialog, show_speaker_sub=opts.show_speaker_sub))
            target = staging / MOD_SCRIPT / "content" / MODULES_REL
            target.mkdir(parents=True)
            for name, data in scripts.items():
                (target / name).write_bytes(data)
            report.mods.append(MOD_SCRIPT)
            overlaps = script_overlaps(game)
            if overlaps:
                report.warnings.append(f"mod อื่นแก้ script ซับไฟล์เดียวกัน ({'; '.join(overlaps)})"
                                       " เกมอาจขึ้น error ตอนคอมไพล์ script ให้รวมด้วย Script Merger"
                                       " หรือเอาเครื่องหมายออกจาก \"ปรับสีและขนาดซับ\" แล้วติดตั้งใหม่")
        except PatchError as exc:
            log.warning("script patch skipped: %s", exc)
            report.warnings.append("script ของเกมเวอร์ชันนี้ไม่ตรงกับที่รองรับ จึงข้ามการปรับสี/ขนาดซับ"
                                   " (ข้อความภาษาไทยยังใช้งานได้ปกติ)")

    if opts.thai_logo:
        try:
            files = [f for f in logo_files(game.content0, scaled(progress, 0.87, 0.9)) if f.path not in leave]
            if files:
                progress(0.9, "บีบอัดไฟล์เมนูที่มีโลโก้ภาษาไทย...")
                write_mod_content(staging / MOD_LOGO / "content", files)
                report.mods.append(MOD_LOGO)
        except (LogoError, BundleError, OSError) as exc:
            log.warning("thai logo skipped: %s", exc)
            report.warnings.append("ไฟล์เมนูของเกมเวอร์ชันนี้ไม่ตรงกับที่รองรับ จึงข้ามการเปลี่ยนโลโก้เป็นภาษาไทย"
                                   " (ข้อความภาษาไทยยังใช้งานได้ปกติ)")

    if opts.compat:
        _build_patches(game, opts, staging, report, scaled(progress, 0.9, 0.93))

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
        "files": _file_hashes(staging, report.mods),
    }
    (staging / MOD_TEXT / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def export_readme(game: GameInfo, mods: list[str], slot: str) -> str:
    folders = "\n".join(f"   - {m}" for m in mods)
    language = "English" if slot == SLOT_EN else "ไทย"
    return (f"ไฟล์ภาษาไทย The Witcher 3 สร้างโดย ThaiW3Setup v{__version__} เมื่อ {time.strftime('%Y-%m-%d %H:%M')}\n"
            "\n"
            "วิธีติดตั้ง\n"
            "1. ปิดเกมก่อน\n"
            f"2. เปิดโฟลเดอร์เกม (โฟลเดอร์ที่มี bin และ content อยู่ข้างใน)\n   {game.path}\n"
            "3. ถ้ายังไม่มีโฟลเดอร์ชื่อ mods ให้สร้างขึ้นมา\n"
            "4. ถ้าในโฟลเดอร์ mods มีโฟลเดอร์ modThai... อยู่แล้ว ให้ลบออกก่อน\n"
            f"5. คัดลอกโฟลเดอร์ต่อไปนี้ทั้งหมดไปไว้ในโฟลเดอร์ mods\n{folders}\n"
            f"6. เข้าเกมแล้วตั้งค่า > ภาษา > ภาษาข้อความเป็น {language}\n"
            "\n"
            "ถอนการติดตั้ง: ลบโฟลเดอร์ modThai... ออกจากโฟลเดอร์ mods ของเกม\n"
            + "".join(f"\n{m.patch} คือแพตช์ภาษาไทยสำหรับ {m.label} สร้างจาก {m.label} ที่อยู่ในเกมตอนนี้\n"
                      f"ต้องติดตั้ง {m.label} ชุดเดียวกันไว้ก่อน และต้องสร้างไฟล์ใหม่ทุกครั้งที่อัปเดต {m.label}\n"
                      f"ถ้าใช้ Mod Manager ให้ตั้ง Priority ของ {m.patch} ให้เลขน้อยกว่า {m.label}\n"
                      for m in COMPAT_MODS.values() if m.patch in mods))


def export(opts: InstallOptions, out_dir: str | os.PathLike, progress: ProgressFn = noop,
           force_download: bool = False) -> InstallReport:
    """Build the mods into out_dir/ThaiW3_mods for the user to copy into the game's mods folder by hand."""
    game = _supported_game(opts)
    opts = replace(opts, compat=_require_compat_sources(game, opts))
    target = Path(out_dir) / EXPORT_DIR
    try:
        _check_writable(target)
    except PermissionError as exc:
        raise PermissionError(f"ไม่มีสิทธิ์เขียนไฟล์ลงโฟลเดอร์ {target}") from exc
    report = InstallReport(output=str(target), compat=list(opts.compat))

    old = legacy_mods(game)
    if old:
        report.warnings.append(f"พบ mod ภาษาไทยตัวเก่าของ w3tu ({', '.join(p.name for p in old)}) ในโฟลเดอร์ mods"
                               " ของเกม ให้ลบออกก่อนคัดลอก ไม่งั้นจะทำงานชนกัน")
    progress(0.0, "ตรวจหา mod ภาษาไทยตัวอื่น...")
    foreign = foreign_thai_mods(game, deep=True)
    if foreign:
        report.warnings.append(f"พบ mod ภาษาไทยจากที่อื่น ({', '.join(p.name for p in foreign)}) ในโฟลเดอร์ mods"
                               " ของเกม ให้ย้ายออกก่อนคัดลอก ไม่งั้นภาษาไทยจะแสดงเพี้ยน")

    staging = Path(tempfile.mkdtemp(prefix="thaiw3_"))
    try:
        _build_mods(game, opts, staging, report, progress, force_download)
        progress(0.93, f"คัดลอกไฟล์ไปที่ {target}...")
        for name in OUR_MODS + PATCH_MODS:
            if (target / name).exists():
                shutil.rmtree(target / name)
        for name in report.mods:
            shutil.copytree(staging / name, target / name)
        (target / EXPORT_README).write_text(export_readme(game, report.mods, opts.slot), encoding="utf-8-sig")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    log.info("exported %s to %s", ", ".join(report.mods), target)
    progress(1.0, "สร้างไฟล์เสร็จแล้ว")
    return report


def export_zip(opts: InstallOptions, out_dir: str | os.PathLike, progress: ProgressFn = noop,
               force_download: bool = False) -> InstallReport:
    """Same payload as export(), packed as a zip with mods/<folder>/ for Mod Manager or manual unpack."""
    game = _supported_game(opts)
    opts = replace(opts, compat=_require_compat_sources(game, opts))
    target = Path(out_dir) / EXPORT_ZIP
    try:
        _check_writable(Path(out_dir))
    except PermissionError as exc:
        raise PermissionError(f"ไม่มีสิทธิ์เขียนไฟล์ลงโฟลเดอร์ {out_dir}") from exc
    report = InstallReport(compat=list(opts.compat))

    old = legacy_mods(game)
    if old:
        report.warnings.append(f"พบ mod ภาษาไทยตัวเก่าของ w3tu ({', '.join(p.name for p in old)}) ในโฟลเดอร์ mods"
                               " ของเกม ให้ลบออกก่อนคัดลอก ไม่งั้นจะทำงานชนกัน")
    progress(0.0, "ตรวจหา mod ภาษาไทยตัวอื่น...")
    foreign = foreign_thai_mods(game, deep=True)
    if foreign:
        report.warnings.append(f"พบ mod ภาษาไทยจากที่อื่น ({', '.join(p.name for p in foreign)}) ในโฟลเดอร์ mods"
                               " ของเกม ให้ย้ายออกก่อนคัดลอก ไม่งั้นภาษาไทยจะแสดงเพี้ยน")

    staging = Path(tempfile.mkdtemp(prefix="thaiw3_"))
    try:
        _build_mods(game, opts, staging, report, progress, force_download)
        progress(0.93, f"สร้างไฟล์ {EXPORT_ZIP}...")
        readme = export_readme(game, report.mods, opts.slot)
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(EXPORT_README, readme.encode("utf-8-sig"))
                for name in report.mods:
                    root = staging / name
                    for f in sorted(root.rglob("*")):
                        if f.is_file():
                            z.write(f, f"mods/{name}/{f.relative_to(root).as_posix()}")
        except PermissionError as exc:
            raise PermissionError(f"ไม่มีสิทธิ์เขียนไฟล์ {target}") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    report.output = str(target)
    log.info("exported zip %s to %s", ", ".join(report.mods), target)
    progress(1.0, "สร้างไฟล์เสร็จแล้ว")
    return report


def check_coverage(opts: InstallOptions, progress: ProgressFn = noop) -> InstallReport:
    """Download the latest translation and custom sheets and count what an install would translate now."""
    game = identify(opts.game_path)
    if not game.supported:
        raise RuntimeError(f"ไม่รองรับเกมในโฟลเดอร์นี้: {game.label}")
    report = InstallReport()
    tr = get_translations(force_download=True, progress=scaled(progress, 0.0, 0.8))
    report.source, report.fetched = tr.source, tr.age_text
    overrides = merged_overrides(opts.custom_sheets, True, scaled(progress, 0.8, 0.95))
    report.custom = len(overrides.strings)
    report.translated, report.total = coverage(game, tr.thai, tr.by_text, overrides)
    progress(1.0, "เช็คคำแปลล่าสุดเสร็จแล้ว")
    return report


def export_patch_zip(opts: InstallOptions, key: str, out_dir: str | os.PathLike, source: str | None = None,
                     progress: ProgressFn = noop) -> InstallReport:
    """A zip of the Thai patch for one UI mod, laid out for The Witcher 3 Mod Manager.

    The mod's files come from the game's mods folder, else from source (a downloaded zip or folder).
    """
    opts.validate()
    mod = COMPAT_MODS[key]
    mods_dir, settings = None, {}
    if opts.game_path:
        game = identify(opts.game_path)
        if game.supported:
            mods_dir, settings = game.mods_dir, mods_settings.read(game.path)
    report = InstallReport(mods=[mod.patch])
    with open_sources(mod, mods_dir, source, settings) as sources:
        report.source = sources.origin
        files, report.warnings = patch_files(sources, opts.font, opts.thai_logo, scaled(progress, 0.0, 0.85))
        info = patch_info(sources, opts.font, opts.thai_logo)
    progress(0.9, f"สร้างไฟล์ {mod.zip_name}...")
    target = Path(out_dir) / mod.zip_name
    staging = Path(tempfile.mkdtemp(prefix="thaiw3_"))
    try:
        folder = staging / "mods" / mod.patch
        write_mod_content(folder / "content", files)
        write_patch_info(folder, info)
        (staging / PATCH_README).write_text(patch_readme(mod, info), encoding="utf-8-sig")
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
                for f in sorted(staging.rglob("*")):
                    if f.is_file():
                        z.write(f, f.relative_to(staging).as_posix())
        except PermissionError as exc:
            raise PermissionError(f"ไม่มีสิทธิ์เขียนไฟล์ {target}") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    report.output = str(target)
    log.info("exported %s patch from %s to %s", mod.label, report.source, target)
    progress(1.0, f"สร้างไฟล์ {mod.zip_name} เสร็จแล้ว")
    return report


def uninstall(game_path: str | os.PathLike) -> list[str]:
    game = identify(game_path)
    removed = [n for n in _our_folders(game) if (game.mods_dir / n).exists()]
    _remove_our_mods(game)
    log.info("uninstalled %s from %s", ", ".join(removed) or "-", game.mods_dir)
    return removed
