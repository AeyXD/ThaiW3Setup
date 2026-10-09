"""Thai patches for other UI mods, starting with Ink and Iron.

A UI mod ships its own fonts_en.redswf and menu panels, so whichever of it and modThai* loads first hides the
other: no Thai glyphs, or the game's own menus instead of the mod's. A patch is a separate mod folder built from
the player's own copy of that mod: its fonts with our Thai glyphs merged in, its panels restyled like
panel_layout does for the game's, its own labels in Thai (compat_text), its menu with the Thai logo. Our main
Thai mods then leave out every file the mod has (patched_paths). The patch goes into the game directly or into a
zip for The Witcher 3 Mod Manager, and must load ahead of the mod it patches (name order, or Priority in
mods.settings).
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import re
import shutil
import struct
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from . import __version__
from .assets import FONT_PATH, TURKISH_I, font_files
from .bundle import BundleError, BundleFile, iter_bundle
from .compat_text import (GWENT_OPPONENT_NAME_DTY, GWENT_PLAYER_NAME_DTY, GWENT_SCORE_DTY,
                          INK_AND_IRON, INK_AND_IRON_TITLE, MARK_Y_FACTOR_TO, translator)
from .logo import MENU_FILES, LogoError, load_logo, patch_menu
from .mods_settings import ModSetting, disabled, loses_to
from .panel_layout import PANELS, ROW_PANELS, STARTUP_PANELS, TOOLTIP_PANELS, LayoutError, restyle_panel
from .progress import ProgressFn, noop
from .swf_font import alias_glyphs, merge_glyphs

log = logging.getLogger(__name__)

PATCH_INFO = "thai_patch.json"
BUNDLE = "blob0.bundle"

MISSING = "missing"      # the mod is not in the game's mods folder
NO_PATCH = "no_patch"    # the mod is there but no patch for it
STALE = "stale"          # the patch was built from other files of the mod, or with another Thai font
PRIORITY = "priority"    # mods.settings loads the mod ahead of the patch
DISABLED = "disabled"    # mods.settings switches the patch off
OVERLAP = "overlap"      # our main Thai mods still carry files the mod has, installed before the mod or patch
ORPHAN = "orphan"        # a patch without the mod it patches
OK = "ok"


@dataclass(frozen=True)
class Step:
    text: str
    states: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CompatMod:
    key: str
    label: str
    prefix: str  # folder names of the mod's parts in mods/
    patch: str   # our patch folder; "mod0000_" sorts ahead of any "modX"
    url: str
    direct_steps: tuple[Step, ...]
    manager_steps: tuple[Step, ...]
    texts: dict[str, str] = field(default_factory=dict, hash=False, compare=False)  # English label in the mod's own code -> Thai
    titles: dict[str, str] = field(default_factory=dict, hash=False, compare=False)  # menu title text, with the Thai logo

    @property
    def zip_name(self) -> str:
        return f"{self.patch.removeprefix('mod0000_')}.zip"

    def owns(self, folder: str) -> bool:
        return folder.lower().startswith(self.prefix.lower())


MAKE_ZIP = "สร้างไฟล์ zip ไว้ copy เอง..."


def _steps(label: str, patch: str, zip_name: str) -> tuple[tuple[Step, ...], tuple[Step, ...]]:
    # primary path in the UI: switch on, then Install / Update
    direct = (
        Step(f"ติดตั้ง {label} ลงเกมก่อน แล้วปิดเกม", frozenset({MISSING})),
        Step("เปิดสวิตช์แพตช์ แล้วกดติดตั้ง / อัปเดต", frozenset({NO_PATCH, OVERLAP})),
        Step(f"ตั้ง Priority ของ {patch} ให้เลขน้อยกว่า {label}", frozenset({PRIORITY, DISABLED})),
        Step(f"อัปเดต {label} หรือเปลี่ยนฟอนต์แล้ว ให้กดติดตั้ง / อัปเดตซ้ำ", frozenset({STALE})),
    )
    # kept for the zip README / export dialog (Mod Manager path is behind the ▼ menu)
    manager = (
        Step(f"ใน Mod Manager ติดตั้ง {label} ก่อน", frozenset({MISSING})),
        Step(f"กด \"{MAKE_ZIP}\" แล้วติดตั้ง {zip_name} ใน Mod Manager", frozenset({NO_PATCH})),
        Step(f"ตั้ง Priority ของ {patch} ให้เลขน้อยกว่า {label}", frozenset({PRIORITY, DISABLED})),
        Step("กลับมาที่โปรแกรมนี้แล้วกดติดตั้ง / อัปเดต", frozenset({OVERLAP})),
        Step(f"อัปเดต {label} แล้ว ให้สร้าง zip ใหม่แล้วติดตั้งทับ", frozenset({STALE})),
    )
    return direct, manager


def _mod(key: str, label: str, prefix: str, patch: str, url: str, texts: dict[str, str],
         titles: dict[str, str]) -> CompatMod:
    direct, manager = _steps(label, patch, f"{patch.removeprefix('mod0000_')}.zip")
    return CompatMod(key, label, prefix, patch, url, direct, manager, texts, titles)


COMPAT_MODS: dict[str, CompatMod] = {m.key: m for m in (
    _mod("inkandiron", "Ink and Iron - UI HUD", "modInkAndIron", "mod0000_ThaiPatch_InkAndIron",
         "https://www.nexusmods.com/witcher3/mods/13111", INK_AND_IRON, INK_AND_IRON_TITLE),
)}


@dataclass
class Sources:
    """The mod's parts found in one place, each part's blob0.bundle as a file on disk."""
    mod: CompatMod
    origin: str
    bundles: dict[str, Path] = field(default_factory=dict)  # part folder name -> blob0.bundle

    def hashes(self) -> dict[str, str]:
        return {name: file_sha1(path) for name, path in sorted(self.bundles.items())}


_sha1_cache: dict[tuple[str, int, int], str] = {}


def file_sha1(path: Path) -> str:
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _sha1_cache:
        h = hashlib.sha1()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        _sha1_cache[key] = h.hexdigest()
    return _sha1_cache[key]


def game_parts(mods_dir: Path, mod: CompatMod, settings: dict[str, ModSetting] | None = None) -> dict[str, Path]:
    """The mod's parts in the game's mods folder that the game loads, with their bundles."""
    if not mods_dir.is_dir():
        return {}
    out = {}
    for p in sorted(mods_dir.iterdir()):
        bundle = p / "content" / BUNDLE
        if p.is_dir() and mod.owns(p.name) and bundle.is_file() and not disabled(p.name, settings or {}):
            out[p.name] = bundle
    return out


def bundle_paths(bundles) -> set[str]:
    """Every file path in the bundles, read from their tables of contents only."""
    names: set[str] = set()
    for bundle in bundles:
        for _ in iter_bundle(bundle, lambda n, _s: names.add(n) and False):
            pass
    return names


def patched_paths(mods_dir: Path, settings: dict[str, ModSetting], patching: set[str],
                  ours: set[str]) -> set[str]:
    """Files our main Thai mods leave to UI mods that get a patch: the patch has them in Thai.
    patching is the keys patched by this install, ours the folders it replaces; a patch from elsewhere
    (the Mod Manager zip) counts too. Without any patch the files stay, else the mod's fonts lose Thai."""
    out: set[str] = set()
    for mod in COMPAT_MODS.values():
        parts = game_parts(mods_dir, mod, settings)
        if parts and (mod.key in patching or any(p not in ours for p in installed_patches(mods_dir, mod))):
            out |= bundle_paths(parts.values())
    return out


def _folder_parts(root: Path, mod: CompatMod) -> dict[str, Path]:
    """Parts anywhere under a downloaded folder: <root>/mods/modX/content/blob0.bundle or shallower."""
    out = {}
    for bundle in sorted(root.rglob(BUNDLE)):
        part = bundle.parent.parent
        if bundle.parent.name.lower() == "content" and mod.owns(part.name):
            out.setdefault(part.name, bundle)
    return out


def _zip_parts(path: Path, mod: CompatMod, tmp: Path) -> dict[str, Path]:
    pattern = re.compile(rf"(?:^|/)({re.escape(mod.prefix)}[^/]*)/content/{BUNDLE}$", re.IGNORECASE)
    out = {}
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            m = pattern.search(name.replace("\\", "/"))
            if not m or m.group(1) in out:
                continue
            target = tmp / m.group(1) / BUNDLE
            target.parent.mkdir(parents=True)
            with z.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            out[m.group(1)] = target
    return out


@contextlib.contextmanager
def open_sources(mod: CompatMod, mods_dir: Path | None, extra: str | Path | None = None,
                 settings: dict[str, ModSetting] | None = None) -> Iterator[Sources]:
    """The mod's parts from the game's mods folder, else from a downloaded zip or folder."""
    parts = game_parts(mods_dir, mod, settings) if mods_dir else {}
    if parts:
        yield Sources(mod, str(mods_dir), parts)
        return
    if not extra:
        raise FileNotFoundError(f"ไม่พบ {mod.label} ในโฟลเดอร์ mods ของเกม ให้เลือกไฟล์ zip หรือโฟลเดอร์ที่ดาวน์โหลดมา")
    path = Path(extra)
    if path.is_dir():
        parts = _folder_parts(path, mod)
        if not parts:
            raise FileNotFoundError(f"ไม่พบไฟล์ของ {mod.label} ในโฟลเดอร์ {path}")
        yield Sources(mod, str(path), parts)
        return
    if path.suffix.lower() in (".7z", ".rar"):
        raise ValueError(f"เปิดไฟล์ {path.suffix} ไม่ได้ ให้แตกไฟล์ {path.name} ก่อน แล้วเลือกโฟลเดอร์ที่แตกออกมาแทน")
    if not zipfile.is_zipfile(path):
        raise FileNotFoundError(f"ไม่พบไฟล์ zip {path}")
    tmp = Path(tempfile.mkdtemp(prefix="thaiw3_compat_"))
    try:
        parts = _zip_parts(path, mod, tmp)
        if not parts:
            raise FileNotFoundError(f"ไม่พบไฟล์ของ {mod.label} ใน {path.name}")
        yield Sources(mod, str(path), parts)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _laid_out(path: str) -> bool:
    return path in STARTUP_PANELS or (path.startswith(PANELS) and path.endswith(".redswf"))


def _wanted(mod: CompatMod, path: str, thai_logo: bool) -> bool:
    return (path == FONT_PATH or _laid_out(path) or (thai_logo and path in MENU_FILES)
            or (bool(mod.texts) and path.endswith(".redswf")))


def _patch_one(mod: CompatMod, path: str, data: bytes, font: str, thai_logo: bool, logo) -> bytes | None:
    if path == FONT_PATH:
        return alias_glyphs(merge_glyphs(data, font_files(font)[0].data), TURKISH_I)
    titles = mod.titles if thai_logo and path in MENU_FILES else None
    texts = translator(mod.texts, titles) if mod.texts or titles else None
    out = None
    if texts or _laid_out(path):
        try:
            out = restyle_panel(data, path in ROW_PANELS, path in TOOLTIP_PANELS, texts, _laid_out(path))
        except LayoutError:
            if _laid_out(path):
                raise
    if thai_logo and path in MENU_FILES:
        out = patch_menu(out or data, logo())
    return out


def patch_files(sources: Sources, font: str, thai_logo: bool,
                progress: ProgressFn = noop) -> tuple[list[BundleFile], list[str]]:
    """The patch's files and warnings for whatever had to be left out."""
    mod = sources.mod
    label = mod.label
    found: dict[str, bytes] = {}
    # the game takes a file from the first folder in name order, so does the patch
    for name, bundle in sorted(sources.bundles.items(), key=lambda kv: kv[0].lower()):
        progress(0.0, f"อ่านไฟล์ {name}...")
        for f in iter_bundle(bundle, lambda n, _s: _wanted(mod, n, thai_logo) and n not in found):
            found[f.path] = f.data
    files, warnings = [], []
    logo_cache: list = []

    def logo():
        if not logo_cache:
            logo_cache.append(load_logo())
        return logo_cache[0]

    for i, (path, data) in enumerate(sorted(found.items())):
        short = path.rsplit("\\", 1)[-1]
        progress(i / max(1, len(found)), f"ทำแพตช์ {label}: {short}...")
        try:
            out = _patch_one(mod, path, data, font, thai_logo, logo)
        except LogoError as exc:
            log.warning("%s logo skipped in %s: %s", label, short, exc)
            warnings.append(f"ใส่โลโก้ภาษาไทยในเมนูของ {label} ไม่ได้ จะเห็นโลโก้ของ {label} แทน")
            try:
                out = _patch_one(mod, path, data, font, False, logo)
            except (LayoutError, BundleError, ValueError, struct.error):
                out = None
        except (LayoutError, BundleError, ValueError, struct.error) as exc:
            log.warning("%s %s left out of the patch: %s", label, short, exc)
            if path == FONT_PATH:
                raise RuntimeError(f"ใส่อักษรไทยลงฟอนต์ของ {label} ไม่ได้ ({exc})") from exc
            continue
        if out is not None:
            files.append(BundleFile(path, out))
    if FONT_PATH not in found:
        warnings.append(f"{label} ชุดนี้ไม่มีไฟล์ฟอนต์ แพตช์จึงมีแค่การจัดบรรทัดหน้าเมนู")
    if not files:
        raise RuntimeError(f"ไม่มีไฟล์ของ {label} ที่ต้องทำแพตช์")
    return files, warnings


def texts_hash(mod: CompatMod) -> str:
    tables = {"texts": mod.texts, "titles": mod.titles, "dialog_mark_y": MARK_Y_FACTOR_TO,
              "gwent_hud": {"opponent_name_dty": GWENT_OPPONENT_NAME_DTY,
                            "player_name_dty": GWENT_PLAYER_NAME_DTY,
                            "score_dty": GWENT_SCORE_DTY}}
    return hashlib.sha1(json.dumps(tables, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def patch_info(sources: Sources, font: str, thai_logo: bool) -> dict:
    return {"mod": sources.mod.key, "version": __version__, "created": time.strftime("%Y-%m-%d %H:%M"),
            "font": font, "thai_logo": thai_logo, "sources": sources.hashes(), "texts": texts_hash(sources.mod)}


def write_patch_info(folder: Path, info: dict) -> None:
    (folder / PATCH_INFO).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def installed_patches(mods_dir: Path, mod: CompatMod) -> dict[str, dict]:
    """Patch folders for mod in mods/, found by their info file since the Mod Manager may rename them."""
    out = {}
    if not mods_dir.is_dir():
        return out
    for p in sorted(mods_dir.iterdir()):
        info = p / PATCH_INFO
        if not info.is_file():
            continue
        try:
            data = json.loads(info.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("mod") == mod.key:
            out[p.name] = data
    return out


@dataclass
class PatchStatus:
    mod: CompatMod
    state: str
    parts: list[str] = field(default_factory=list)
    patch: str = ""
    ahead: list[str] = field(default_factory=list)  # parts loading ahead of the patch, or OVERLAP's files

    @property
    def short(self) -> str:
        return {
            MISSING: "ไม่พบในเกม",
            NO_PATCH: "ต้องทำแพตช์",
            STALE: "แพตช์ล้าสมัย",
            PRIORITY: "ต้องตั้ง Priority",
            DISABLED: "แพตช์ถูกปิด",
            OVERLAP: "ภาษาไทยยังทับอยู่",
            ORPHAN: "แพตช์ค้าง",
            OK: "พร้อมใช้",
        }[self.state]

    @property
    def message(self) -> str:
        m = self.mod
        return {
            MISSING: f"ไม่พบ {m.label} ในโฟลเดอร์ mods",
            NO_PATCH: f"พบ {m.label} ({len(self.parts)} ส่วน) แต่ยังไม่มีแพตช์ภาษาไทย",
            STALE: f"แพตช์ {self.patch} สร้างจาก {m.label} คนละชุด คนละฟอนต์ หรือคำแปลรุ่นเก่า ให้ทำแพตช์ใหม่",
            PRIORITY: f"{', '.join(self.ahead)} โหลดก่อนแพตช์ ให้ตั้ง Priority ของ {self.patch} ให้เลขน้อยกว่า",
            DISABLED: f"แพตช์ {self.patch} ถูกปิดอยู่ใน Mod Manager / mods.settings",
            OVERLAP: f"ภาษาไทยหลักยังมีไฟล์ที่ทับ {m.label} ({len(self.ahead)} ไฟล์) ให้กดติดตั้ง / อัปเดตอีกครั้ง",
            ORPHAN: f"พบแพตช์ {self.patch} แต่ไม่พบ {m.label} ให้ลบหรือปิดแพตช์",
            OK: f"พบ {m.label} ({len(self.parts)} ส่วน) และแพตช์ {self.patch} พร้อมใช้",
        }[self.state]

    @property
    def tone(self) -> str:
        """Label style suffix: Ok, Warn, Bad, or '' (default)."""
        if self.state == OK:
            return "Ok"
        if self.state in (MISSING, ORPHAN):
            return ""
        if self.state == DISABLED:
            return "Bad"
        return "Warn"

    def step(self, steps: tuple[Step, ...] | None = None) -> int | None:
        items = steps if steps is not None else self.mod.direct_steps
        return next((i for i, s in enumerate(items) if self.state in s.states), None)

    def next_action(self) -> tuple[str, str, str | None]:
        """(title, text, primary button id or None): pick | install."""
        m = self.mod
        if self.state == OK:
            return "พร้อมใช้แล้ว", f"{m.label} และแพตช์ทำงานร่วมกันได้", None
        if self.state == MISSING:
            return ("ขั้นถัดไป",
                    f"ยังไม่พบ {m.label} ในโฟลเดอร์ mods ให้เลือกไฟล์ที่ดาวน์โหลดมา หรือติดตั้ง {m.label} ลงเกมก่อน",
                    "pick")
        if self.state == ORPHAN:
            return "ขั้นถัดไป", f"พบแพตช์ค้างอยู่ แต่ไม่พบ {m.label} ให้ลบหรือปิด {self.patch}", None
        if self.state in (NO_PATCH, OVERLAP, STALE):
            text = {
                STALE: "แพตช์ล้าสมัย กดติดตั้ง / อัปเดตด้านล่าง",
                OVERLAP: "ภาษาไทยหลักยังทับไฟล์อยู่ กดติดตั้ง / อัปเดตด้านล่าง",
                NO_PATCH: "เปิดสวิตช์ด้านบน แล้วกดติดตั้ง / อัปเดตด้านล่าง",
            }[self.state]
            return "ขั้นถัดไป", text, "install"
        if self.state == DISABLED:
            return "ขั้นถัดไป", "เปิดแพตช์ใน Mod Manager / mods.settings", None
        if self.state == PRIORITY:
            return "ขั้นถัดไป", "ตั้ง Priority ของแพตช์ให้เลขน้อยกว่า mod ต้นทาง", None
        return "ขั้นถัดไป", self.message, None


def patch_status(mods_dir: Path, mod: CompatMod, settings: dict[str, ModSetting], font: str | None = None,
                 main: tuple[str, ...] = ()) -> PatchStatus:
    """main: our main Thai mod folders, which must not carry the mod's files once it has a patch."""
    parts = game_parts(mods_dir, mod, settings)
    patches = installed_patches(mods_dir, mod)
    if not parts:
        return PatchStatus(mod, ORPHAN if patches else MISSING, patch=next(iter(patches), ""))
    names = sorted(parts)
    if not patches:
        return PatchStatus(mod, NO_PATCH, names)
    patch, info = next(iter(patches.items()))
    try:
        current = {name: file_sha1(path) for name, path in parts.items()}
    except OSError:
        current = {}
    if (current != info.get("sources") or (font and info.get("font") != font)
            or info.get("texts") != texts_hash(mod)):
        return PatchStatus(mod, STALE, names, patch)
    if disabled(patch, settings):
        return PatchStatus(mod, DISABLED, names, patch)
    ahead = loses_to(patch, names, settings)
    if ahead:
        return PatchStatus(mod, PRIORITY, names, patch, ahead)
    ours = [b for b in (mods_dir / m / "content" / BUNDLE for m in main) if b.is_file()]
    try:
        overlap = sorted(bundle_paths(ours) & bundle_paths(parts.values()))
    except (OSError, BundleError):
        overlap = []
    if overlap:
        return PatchStatus(mod, OVERLAP, names, patch, overlap)
    return PatchStatus(mod, OK, names, patch)


def patch_readme(mod: CompatMod, info: dict) -> str:
    # whoever reads it has the zip already
    after = [f"ติดตั้งไฟล์ {mod.zip_name} นี้ใน Mod Manager" if MAKE_ZIP in s.text else s.text
             for s in mod.manager_steps]
    steps = "\n".join(f"{i}. {text}" for i, text in enumerate(after, start=1))
    parts = "\n".join(f"   - {name}" for name in info["sources"])
    return (f"แพตช์ภาษาไทยสำหรับ {mod.label} สร้างโดย ThaiW3Setup v{__version__} เมื่อ {info['created']}\n"
            f"ฟอนต์ไทย: {info['font']}\n"
            f"สร้างจาก {mod.label} ส่วนต่อไปนี้\n{parts}\n"
            "\n"
            f"แพตช์นี้แปลข้อความของ {mod.label} เป็นภาษาไทย ใส่อักษรไทยในฟอนต์ และจัดบรรทัดหน้าเมนูให้อ่านภาษาไทยได้\n"
            f"หน้าตั้งค่าของ {mod.label} ยังเป็นภาษาอังกฤษ\n"
            f"ภาษาไทยหลัก (modThai...) ต้องติดตั้งด้วย ThaiW3Setup หลังลงแพตช์นี้ เพื่อให้เว้นไฟล์ของ {mod.label} ไว้\n"
            "\n"
            f"วิธีติดตั้งด้วย The Witcher 3 Mod Manager\n{steps}\n"
            "\n"
            f"ติดตั้งเอง: คัดลอกโฟลเดอร์ mods/{mod.patch} ไปไว้ในโฟลเดอร์ mods ของเกม\n"
            f"ถ้าเลิกใช้ {mod.label} ให้ลบหรือปิด {mod.patch} ด้วย\n")
