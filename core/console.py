"""Console (PS5 / Xbox Series X|S / Switch 2) packages for mod.io.

CD Projekt RED's cross-platform rules let players install mods from mod.io on every
platform, but mods that patch game scripts must be built with REDkit to be approved.
Everything ThaiW3Setup ships except the subtitle-style script mod is bundle/asset
content, so a console build simply leaves the script mod out; subtitle colours, sizes
and positions only ever applied through that script mod and are reset here.
"""
from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import __version__
from .game_detect import GameInfo
from .options import InstallOptions, MODE_THAI

CONSOLE_DIR = "ThaiW3_console"
BUILD_INFO = "build-info.json"
GUIDE_NAME = "อัปโหลด-modio.md"
HOWTO_URL = "https://mod.io/g/the-witcher-3/r/how-to-create-mods-for-cross-platform-mod-support"
SUPPORT_URL = "https://support.cdprojektred.com/en/witcher-3/pc/gameplay/issue/3001/cross-platform-mod-support-how-to"
# zips carry no real timestamps, so rebuilds of the same content byte-compare
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

# options that survive into the console packages; everything else resets to defaults
# (mode is forced to Thai-only: the "  [English]" separator that combine() writes only
# becomes a second subtitle line through the console-excluded script mod)
_CONSOLE_FIELDS = ("font", "storybook", "thai_logo", "slot", "custom_sheets")

# the only file shape, short of build-info's own list, that counts as our zip:
# one of our mod names + a full version + the .zip suffix
_ZIP_NAME = re.compile(r"(?:modThaiText|modThaiFont|modThaiStoryBook|modThaiLogo|modThaiDoubleSub)"
                       r"-\d+\.\d+(?:\.\d+)?\.zip")

MOD_LABELS = {
    "modThaiText": "ข้อความภาษาไทยของทั้งเกม (แปลไทย พร้อมตัดคำไทยในตัว)",
    "modThaiFont": "ฟอนต์ภาษาไทยสำหรับ UI และซับ ไม่มี mod นี้ตัวอักษรไทยจะเป็นสี่เหลี่ยม",
    "modThaiStoryBook": "ซับไทยของคัตซีน Storybook",
    "modThaiLogo": "โลโก้ภาษาไทยในเมนูหลักและหน้ากดปุ่มเริ่มเกม",
}


def console_options(opts: InstallOptions) -> InstallOptions:
    """Build options trimmed to what ships in the console packages.

    The subtitle script mod is console-excluded (REDkit only), so every option that
    only reaches the game through it (colours, sizes, HUD offsets) resets to default.
    """
    base = InstallOptions()
    base.game_path = opts.game_path
    base.subtitle_style = False  # the script mod is console-excluded (REDkit only)
    base.mode = MODE_THAI
    for name in _CONSOLE_FIELDS:
        setattr(base, name, getattr(opts, name))
    base.validate()
    return base


def clean_console_target(target: Path) -> list[str]:
    """Remove a previous console export's files so the folder matches this build's set.

    Deletes the zips the previous build recorded in build-info.json — that catches
    renames and mods disabled this run — plus the rewritten build info and guide.
    When build-info is missing or corrupt, a strict shape check is the fallback: one
    of our mod names, a full X.Y[.Z] version and a .zip suffix, nothing else, so
    files like modThaiText-review-notes.md are never touched.
    """
    removed = []
    if not target.is_dir():
        return removed
    recorded = _recorded_zips(target)
    for f in sorted(target.iterdir()):
        if not f.is_file():
            continue
        if f.name in recorded or f.name in (BUILD_INFO, GUIDE_NAME) or _ZIP_NAME.fullmatch(f.name):
            f.unlink()
            removed.append(f.name)
    return removed


def _recorded_zips(target: Path) -> set[str]:
    try:
        data = json.loads((target / BUILD_INFO).read_text(encoding="utf-8"))
        mods = data.get("mods")
        return {m.get("zip") for m in mods.values()
                if isinstance(m, dict) and isinstance(m.get("zip"), str)}
    except (OSError, ValueError, AttributeError):
        return set()


def publish_packages(package_dir: Path, target: Path) -> list[str]:
    """Swap a fully built package set into target, leaving foreign files in place.

    Runs only after the new set exists in full, so a build that fails partway never
    touches the previous export; on success the folder matches the new build-info.
    """
    removed = clean_console_target(target)
    target.mkdir(parents=True, exist_ok=True)
    for f in sorted(package_dir.iterdir()):
        shutil.move(str(f), target / f.name)
    return removed


def zip_mod(mod_dir: Path, dest: Path) -> None:
    """Zip a built mod folder with the mod folder itself at the zip root, the layout
    the game's mods directory expects. Deterministic: same content in, same bytes out."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in sorted(mod_dir.rglob("*")):
            if not f.is_file():
                continue
            info = zipfile.ZipInfo(f"{mod_dir.name}/{f.relative_to(mod_dir).as_posix()}", date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, f.read_bytes())


@dataclass
class ConsoleGuideInput:
    game: GameInfo
    mods: list[str]
    zips: dict[str, str]  # mod folder name -> zip file name
    font: str
    mode: str
    slot: str
    translated: int
    total: int
    percent: float


def _mode_label(mode: str) -> str:
    return "ซับสองภาษา ไทย + อังกฤษ" if mode == "double" else "ซับไทยอย่างเดียว"


def console_guide(info: ConsoleGuideInput) -> str:
    files = "\n".join(f"- `{name}` — {MOD_LABELS.get(mod, mod)}" for mod, name in sorted(info.zips.items()))
    language = "English (โหมดแทนภาษาอังกฤษ)" if info.slot == "en" else "ไทย (Thai) ในเมนู Text Language"
    return f"""# แพ็กเกจ mod.io สำหรับคอนโซล (PS5 / Xbox Series X|S / Switch 2)

สร้างโดย ThaiW3Setup v{__version__} เมื่อ {date.today().isoformat()} จากเกม {info.game.edition}
เวอร์ชัน {info.game.version or 'ไม่ทราบ'} (แปลแล้ว {info.percent:.2f}% จากคำแปล {info.translated}/{info.total} ข้อความ)
โหมดที่ build: ฟอนต์ {info.font} / {_mode_label(info.mode)} / ช่องภาษา {info.slot}

## ไฟล์ในโฟลเดอร์นี้

{files}
- `{BUILD_INFO}` — รายละเอียด build และค่า hash ของแต่ละ zip สำหรับเทียบเวอร์ชัน

## สิ่งที่แพ็กเกจนี้ไม่มี (ต่างจาก PC)

mod สคริปต์ปรับสี ขนาด และตำแหน่งซับ (`modThaiDoubleSub`) ไม่อยู่ในแพ็กเกจ เพราะกติกาของ
CD Projekt RED กำหนดให้ mod ที่แก้สคริปต์ต้องสร้างด้วย REDkit จึงจะอนุมัติขึ้นคอนโซลได้
ซับบนคอนโซลจึงใช้สี ขนาด และตำแหน่งมาตรฐานของเกม และ build คอนโซลจำกัดไว้ที่
**ซับไทยอย่างเดียว** เพราะโหมดสองภาษาพึ่งสคริปต์ตัวเดียวกันในการตัดตัวคั่น
"  [English]" ออกเป็นบรรทัดที่สองของซับ ไม่มีสคริปต์แล้วภาษาอังกฤษจะต่อท้ายบรรทัดเดียวกัน
จะเปิดโหมดสองภาษาอีกครั้งเมื่อมีสคริปต์ mod เวอร์ชัน REDkit หรือได้ทดสอบการแสดงผลบนคอนโซลจริง

## วิธีอัปโหลด (ครั้งแรก)

1. สมัครบัญชี mod.io แล้วเชื่อมกับบัญชี CD PROJEKT RED (ใช้เมนู Mods ในเกมเพื่อเชื่อมก็ได้)
2. อ่านคู่มือทางการ [How-to: Create Mods for Cross-Platform Mod Support]({HOWTO_URL})
   และ[หน้า support เรื่อง Cross-Platform Mod Support]({SUPPORT_URL}) ของ CD Projekt RED
   โดยเฉพาะหัวข้อโครงสร้างไฟล์ — zip ของเราวางโฟลเดอร์ mod (`modThai...`) ไว้ที่รากของ zip
   ถ้าคู่มือกำหนดรูปแบบอื่นให้แก้ `core/console.py` (ฟังก์ชัน `zip_mod`) ให้ตรงก่อนอัปโหลด
3. ทีละ zip: เปิด {HOWTO_URL.rsplit('/', 3)[0]} → Add mod → ตั้งชื่อเดียวกับโฟลเดอร์ mod
   ใน zip (เช่น modThaiText) → อัปโหลด zip → เลือกหมวดให้ตรง (เช่น Localization / GUI)
   และเขียนคำอธิบายไทย + อังกฤษสั้น ๆ
4. แจ้งทีม mod.io / CD Projekt RED ว่าต้องการให้ mod ใช้ได้บนคอนโซล แล้วรอการอนุมัติ
   ผลจะเห็นเป็นแท็ก **Available on consoles** บนหน้า mod

## เช็กลิสต์ทดสอบบน PS5 (ก่อนประกาศให้ชุมชน)

1. เปิดใช้ modThaiText ตัวเดียว → Options > Language > Text Language ต้องขึ้น
   "{language}" และข้อความในเกมเป็นภาษาไทยจริง (ไม่ใช่อังกฤษหรือตุรกี)
2. เพิ่ม modThaiFont → ตัวอักษรไทยต้องไม่เป็นสี่เหลี่ยม (tofu) ทั้งในเมนู ซับ และ journal
3. เพิ่ม modThaiStoryBook (ถ้า build) → คัตซีนเปิดเรื่องต้องมีซับไทย
4. ปิดการใช้ mod ทั้งหมด → เกมต้องกลับมาเป็นภาษาเดิมโดยไม่พัง
5. ถ้าข้อ 1 ไม่ผ่าน (เมนูภาษาไม่แสดงรายการไทย) ไล่ตรวจหาสาเหตุตามลำดับก่อนสรุปอะไร
   ก. เมนู Mods ในเกม: modThaiText ต้องปรากฏและอยู่ในสถานะเปิดใช้ — ถ้าไม่ปรากฏเลย
      ปัญหาอยู่ที่การอัปโหลดหรือการโหลด mod ไม่ใช่เนื้อหาของ mod
   ข. สลับ Text Language ไปภาษาอื่นแล้วสลับกลับ แล้วปิด-เปิดเกมใหม่อีกครั้ง
   ค. เทียบ game_version ใน build-info.json กับเวอร์ชันเกมบนเครื่องทดสอบ
      ต้องเป็นเกมเวอร์ชันเดียวกับที่ใช้ build
   ง. ถ้าครบทุกข้อแล้วรายการไทยยังไม่ขึ้น เก็บหลักฐาน (ภาพหน้าจอ เวอร์ชันเกม
      รายชื่อ mod ที่เปิดใช้) แล้วเปิด issue ใน repo ก่อนเผยแพร่ — ถึงตรงนี้ค่อยมี
      ข้อมูลพอจะแยกว่าเป็นข้อจำกัดของคอนโซลหรือปัญหาของแพ็กเกจ

## ข้อควรรู้สำหรับผู้เล่นคอนโซล (แนะนำให้ใส่ในคำอธิบายบน mod.io)

- ต้องล็อกอินบัญชี CD PROJEKT RED ที่เชื่อมกับ mod.io ผ่านเมนู Mods ในเกม
- เซฟที่สร้างขณะเปิดใช้ mod ถูกทำเครื่องหมายว่าเป็นเซฟที่ใช้ mod และทรอฟี่/achievements
  จะถูกปิดในเซฟลักษณะนี้
- การย้ายเซฟข้ามแพลตฟอร์มควรเปิดชุด mod เดียวกันทั้งสองฝั่ง ไม่อย่างนั้นเซฟอาจโหลดไม่ถูกต้อง
- อยากเปลี่ยนฟอนต์หรือเปลี่ยนโหมดซับ ต้องรอ variant อื่นที่อัปโหลดแยกต่างหาก

## อัปเดตคำแปลหรือเกมเวอร์ชันใหม่

รันคำสั่ง build ใหม่ (ดู modio-console.md ใน repo) แล้วอัปโหลด zip ใหม่ไปเป็น
ไฟล์เวอร์ชันถัดไปของ mod เดิมบน mod.io อย่าสร้างหน้า mod ใหม่
"""
