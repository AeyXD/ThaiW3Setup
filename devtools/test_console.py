"""Console packaging: the preset drops script-only options and zips carry the mod folder at their root."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile

from core.console import ConsoleGuideInput, console_guide, console_options, zip_mod
from core.game_detect import GameInfo
from core.options import InstallOptions, MODE_DOUBLE

# console preset keeps only what ships in the packages
pc = replace(InstallOptions(), font="Sarabun", mode=MODE_DOUBLE, sub_y=-10.0, sub_width=120,
             choice_scale=80, color1="#FF0000", size1=40, thai_logo=True)
con = console_options(pc)
defaults = InstallOptions()
assert con.subtitle_style is False
assert (con.sub_y, con.sub_width, con.choice_scale, con.color1, con.size1) == \
       (defaults.sub_y, defaults.sub_width, defaults.choice_scale, defaults.color1, defaults.size1)
assert (con.font, con.mode, con.thai_logo, con.slot) == (pc.font, pc.mode, pc.thai_logo, pc.slot)
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

# the guide names every zip and states the script-mod exclusion
guide = console_guide(ConsoleGuideInput(
    GameInfo(Path("/g"), "remastered"), ["modThaiText", "modThaiFont"],
    {"modThaiText": "modThaiText-0.0.0.zip", "modThaiFont": "modThaiFont-0.0.0.zip"},
    "Sarabun", MODE_DOUBLE, "tr", 90, 100, 90.0))
for needle in ("modThaiText-0.0.0.zip", "modThaiFont-0.0.0.zip", "REDkit", "Available on consoles",
               "ไม่อยู่ในแพ็กเกจ", "ซับสองภาษา"):
    assert needle in guide, needle
print("test_console ok")
