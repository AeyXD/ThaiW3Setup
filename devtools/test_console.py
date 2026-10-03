"""Console packaging: Thai-only preset, manifest-matched output cleanup, mod-rooted zips."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile

from core.console import (BUILD_INFO, GUIDE_NAME, ConsoleGuideInput, clean_console_target,
                          console_guide, console_options, zip_mod)
from core.game_detect import GameInfo
from core.options import InstallOptions, MODE_DOUBLE, MODE_THAI

# the console preset keeps only what ships in the packages and forces Thai-only subtitles:
# the "  [English]" separator that combine() writes only becomes a second line through
# the console-excluded script mod, so double mode would render both languages inline
pc = replace(InstallOptions(), font="Sarabun", mode=MODE_DOUBLE, thai_first=False, sub_y=-10.0,
             sub_width=120, choice_scale=80, color1="#FF0000", size1=40, thai_logo=True)
con = console_options(pc)
defaults = InstallOptions()
assert con.subtitle_style is False
assert con.mode == MODE_THAI, "console builds must be Thai-only"
assert con.thai_first == defaults.thai_first
assert (con.sub_y, con.sub_width, con.choice_scale, con.color1, con.size1) == \
       (defaults.sub_y, defaults.sub_width, defaults.choice_scale, defaults.color1, defaults.size1)
assert (con.font, con.thai_logo, con.slot) == (pc.font, pc.thai_logo, pc.slot)
assert con.custom_sheets == pc.custom_sheets
assert con.game_path == pc.game_path
con.validate()

# zips root at the mod folder and rebuild byte-identical for the same content
mod = Path(tempfile.mkdtemp()) / "modThaiText"
(mod / "content").mkdir(parents=True)
(mod / "content" / "blob0.bundle").write_bytes(b"bundle")
(mod / "content" / "metadata.store").write_bytes(b"meta")
one, two = Path(tempfile.mkdtemp()) / "a.zip", Path(tempfile.mkdtemp()) / "b.zip"
zip_mod(mod, one)
zip_mod(mod, two)
assert one.read_bytes() == two.read_bytes(), "same content should zip identically"
with ZipFile(one) as zf:
    assert zf.namelist() == ["modThaiText/content/blob0.bundle", "modThaiText/content/metadata.store"]
    assert zf.read("modThaiText/content/blob0.bundle") == b"bundle"

# re-export drops the previous run's zips (any version, mods disabled included) so the
# folder matches the new build-info; anything not ours stays untouched
target = Path(tempfile.mkdtemp()) / "ThaiW3_console"
target.mkdir()
stale = ["modThaiStoryBook-0.3.0.zip", "modThaiText-0.3.0.zip", "modThaiDoubleSub-0.3.0.zip",
         BUILD_INFO, GUIDE_NAME]
for name in stale:
    (target / name).write_bytes(b"old")
(target / "โน้ตของฉัน.txt").write_bytes(b"mine")
removed = clean_console_target(target)
assert sorted(removed) == sorted(stale), removed
assert [p.name for p in target.iterdir()] == ["โน้ตของฉัน.txt"]
assert clean_console_target(Path(tempfile.mkdtemp()) / "nope") == []

# the guide names every zip, states the script-mod exclusion and Thai-only limit, and
# quotes save behaviour the way CDPR documents it rather than overpromising
guide = console_guide(ConsoleGuideInput(
    GameInfo(Path("/g"), "remastered"), ["modThaiText", "modThaiFont"],
    {"modThaiText": "modThaiText-0.0.0.zip", "modThaiFont": "modThaiFont-0.0.0.zip"},
    "Sarabun", MODE_THAI, "tr", 90, 100, 90.0))
for needle in ("modThaiText-0.0.0.zip", "modThaiFont-0.0.0.zip", "REDkit", "Available on consoles",
               "ไม่อยู่ในแพ็กเกจ", "ซับไทยอย่างเดียว", "อาจโหลดไม่ถูกต้อง"):
    assert needle in guide, needle
assert "ชั่วคราว" not in guide, "do not claim trophies come back"
print("test_console ok")
