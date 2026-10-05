"""Console packaging: Thai-only preset, manifest-matched output cleanup, mod-rooted zips."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile

from core.console import (BUILD_INFO, GUIDE_NAME, ConsoleGuideInput, clean_console_target,
                          console_guide, console_options, publish_packages, zip_mod)
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

# re-export drops the previous run's recorded zips (any version, mods disabled included)
# so the folder matches the new build-info; anything not a zip of ours stays untouched
target = Path(tempfile.mkdtemp()) / "ThaiW3_console"
target.mkdir()
stale = ["modThaiStoryBook-0.3.0.zip", "modThaiText-0.3.0.zip", "modThaiDoubleSub-0.3.0.zip",
         BUILD_INFO, GUIDE_NAME]
for name in stale:
    (target / name).write_bytes(b"old")
# build-info lists a renamed zip too, which the shape check alone would miss
(target / "modThaiText-0.3.0-renamed.zip").write_bytes(b"old")
(target / "โน้ตของฉัน.txt").write_bytes(b"mine")
(target / "modThaiText-review-notes.md").write_bytes(b"review")
(target / "modThaiText-latest.zip").write_bytes(b"not-a-version")
import json as _json
(target / BUILD_INFO).write_text(_json.dumps(
    {"mods": {"modThaiText": {"zip": "modThaiText-0.3.0-renamed.zip"}}}), encoding="utf-8")
removed = clean_console_target(target)
assert sorted(removed) == sorted(stale + ["modThaiText-0.3.0-renamed.zip"]), removed
assert sorted(p.name for p in target.iterdir()) == ["modThaiText-latest.zip",
                                                    "modThaiText-review-notes.md", "โน้ตของฉัน.txt"]
# corrupt build-info falls back to the strict zip shape; build-info itself always goes
# because every build rewrites it
(target / BUILD_INFO).write_text("{oops", encoding="utf-8")
assert clean_console_target(target) == [BUILD_INFO]
(target / "modThaiFont-0.3.0.zip").write_bytes(b"old")
assert clean_console_target(target) == ["modThaiFont-0.3.0.zip"]
assert clean_console_target(Path(tempfile.mkdtemp()) / "nope") == []

# publish swaps a fully built set in only when called: the previous export survives a
# build that fails partway because nothing touches the target until then
pkg = Path(tempfile.mkdtemp())
for name in ("modThaiText-1.0.0.zip", "modThaiFont-1.0.0.zip", BUILD_INFO, GUIDE_NAME):
    (pkg / name).write_bytes(b"new")
removed = publish_packages(pkg, target)
assert removed == []
assert sorted(p.name for p in target.iterdir()) == sorted(
    ["modThaiText-1.0.0.zip", "modThaiFont-1.0.0.zip", BUILD_INFO, GUIDE_NAME,
     "modThaiText-latest.zip", "modThaiText-review-notes.md", "โน้ตของฉัน.txt"])
assert list(pkg.iterdir()) == [], "files move out of the staging package dir"

# a swap that fails partway (disk full, unwritable target) rolls the old set back:
# one new file lands, the second refuses to move, and the folder ends up exactly as
# it started — old zips and build-info intact, no half-new files, no backup litter
old = Path(tempfile.mkdtemp()) / "ThaiW3_console"
old.mkdir()
for name in ("modThaiText-0.3.0.zip", "modThaiFont-0.3.0.zip", BUILD_INFO, GUIDE_NAME):
    (old / name).write_bytes(b"old")
(old / "โน้ตของฉัน.txt").write_bytes(b"mine")
pkg2 = Path(tempfile.mkdtemp())
for name in ("modThaiText-1.0.0.zip", "modThaiFont-1.0.0.zip", BUILD_INFO, GUIDE_NAME):
    (pkg2 / name).write_bytes(b"new")

import shutil as _shutil
import core.console as _console
_real_move = _shutil.move

def _move_that_fills_disk(src, dst):
    if Path(dst).name == "modThaiFont-1.0.0.zip":
        raise OSError(28, "simulated disk full")
    return _real_move(src, dst)

_console.shutil.move = _move_that_fills_disk
try:
    publish_packages(pkg2, old)
    raise AssertionError("simulated failure did not propagate")
except OSError:
    pass
finally:
    _console.shutil.move = _real_move
assert sorted(p.name for p in old.iterdir()) == sorted(
    ["modThaiText-0.3.0.zip", "modThaiFont-0.3.0.zip", BUILD_INFO, GUIDE_NAME, "โน้ตของฉัน.txt"])
assert (old / BUILD_INFO).read_bytes() == b"old", "rollback must restore old content"
assert not (old / "modThaiText-1.0.0.zip").exists(), "half-moved new file must not survive"
assert not any(p.name.startswith(".ThaiW3_console-old-") for p in old.parent.iterdir()), \
    "backup dir must be cleaned up after rollback"

# after the fault clears, a rebuilt package set (the staged one was consumed by the
# failed attempt) publishes cleanly; removed comes back sorted
for name in ("modThaiText-1.0.0.zip", "modThaiFont-1.0.0.zip", BUILD_INFO, GUIDE_NAME):
    (pkg2 / name).write_bytes(b"new")
assert publish_packages(pkg2, old) == [BUILD_INFO, "modThaiFont-0.3.0.zip",
                                       "modThaiText-0.3.0.zip", GUIDE_NAME]

# a cross-drive move copies before deleting, so a failure can leave a partially
# written new zip at the target even though shutil.move never returned; the rollback
# must take that half-written file with it, not leave a corrupt zip next to the old set
old3 = Path(tempfile.mkdtemp()) / "ThaiW3_console"
old3.mkdir()
for name in ("modThaiText-0.3.0.zip", BUILD_INFO, GUIDE_NAME):
    (old3 / name).write_bytes(b"old")
pkg3 = Path(tempfile.mkdtemp())
for name in ("modThaiText-1.0.0.zip", BUILD_INFO, GUIDE_NAME):
    (pkg3 / name).write_bytes(b"new")

def _move_that_copies_partially(src, dst):
    if Path(dst).name == "modThaiText-1.0.0.zip":
        Path(dst).write_bytes(b"new-but-trunca")  # copy got this far before ENOSPC
        raise OSError(28, "simulated disk full mid-copy")
    return _real_move(src, dst)

_console.shutil.move = _move_that_copies_partially
try:
    publish_packages(pkg3, old3)
    raise AssertionError("simulated failure did not propagate")
except OSError:
    pass
finally:
    _console.shutil.move = _real_move
assert not (old3 / "modThaiText-1.0.0.zip").exists(), "half-written new zip must not survive"
assert sorted(p.name for p in old3.iterdir()) == [BUILD_INFO, "modThaiText-0.3.0.zip", GUIDE_NAME]
assert (old3 / "modThaiText-0.3.0.zip").read_bytes() == b"old"
assert not any(p.name.startswith(".ThaiW3_console-old-") for p in old3.parent.iterdir())
assert sorted(p.name for p in old.iterdir()) == sorted(
    ["modThaiText-1.0.0.zip", "modThaiFont-1.0.0.zip", BUILD_INFO, GUIDE_NAME, "โน้ตของฉัน.txt"])
assert list(pkg2.iterdir()) == []

# the guide names every zip, states the script-mod exclusion and Thai-only limit, and
# quotes save behaviour the way CDPR documents it rather than overpromising
guide = console_guide(ConsoleGuideInput(
    GameInfo(Path("/g"), "remastered"), ["modThaiText", "modThaiFont"],
    {"modThaiText": "modThaiText-0.0.0.zip", "modThaiFont": "modThaiFont-0.0.0.zip"},
    "Sarabun", MODE_THAI, "tr", 90, 100, 90.0))
for needle in ("modThaiText-0.0.0.zip", "modThaiFont-0.0.0.zip", "REDkit", "Available on consoles",
               "ไม่อยู่ในแพ็กเกจ", "ซับไทยอย่างเดียว", "อาจโหลดไม่ถูกต้อง",
               "ไล่ตรวจหาสาเหตุตามลำดับ", "เปิด issue",
               "แพ็กเกจทดลอง", "ยังไม่ได้รับการยืนยันบนคอนโซล"):
    assert needle in guide, needle
assert "โผล่ขึ้นมาใหม่" in guide, "tr build expects a new Thai menu entry"
# the pass bar checks translated samples with the font enabled, not "everything Thai"
assert "พร้อม modThaiFont" in guide and "ยังไม่ครบ 100%" in guide and "ทั้งหมด" not in guide.split("## เช็กลิสต์")[1].split("\n2.")[0]

# the en-slot build replaces the English slot, so the checklist must tell the tester
# to pick English and expect Thai text — not to hunt for a new Thai entry
en_guide = console_guide(ConsoleGuideInput(
    GameInfo(Path("/g"), "remastered"), ["modThaiText"],
    {"modThaiText": "modThaiText-0.0.0.zip"}, "Sarabun", MODE_THAI, "en", 90, 100, 90.0))
assert "โหมดแทนภาษาอังกฤษ" in en_guide and "English" in en_guide
assert "โผล่ขึ้นมาใหม่" not in en_guide, "en build has no new menu entry to look for"
assert "พร้อม modThaiFont" in en_guide and "ยังไม่ครบ 100%" in en_guide
assert "ชั่วคราว" not in guide, "do not claim trophies come back"
assert "ไม่ใช่ข้อผิดพลาดของแพ็กเกจ" not in guide, "do not diagnose the language menu upfront"

# export-console is a one-off build and must not persist its preset into the shared
# installer settings; the PC export keeps saving as before
import core.cli as _cli
from core.installer import InstallReport

_calls = {}
_cli.load_options = lambda: InstallOptions(game_path="/g")

def _fake_console_export(opts, out, progress, force_download):
    _calls["console_opts"] = opts
    return InstallReport(output=str(out))

_cli.export_console = _fake_console_export
_cli.export = lambda opts, out, progress, force_download: InstallReport(output=str(out))
_cli.save_options = lambda opts: _calls.setdefault("saved", opts)
_cli.main(["export-console", "--game", "/g", "--out", "/tmp/anywhere", "--font", "Sarabun"])
assert "saved" not in _calls, "export-console must not touch installer settings"
assert _calls["console_opts"].font == "Sarabun", "CLI overrides still reach the build"
_calls.pop("console_opts")
_cli.main(["export", "--game", "/g", "--out", "/tmp/anywhere", "--font", "Sarabun"])
assert "saved" in _calls, "PC export keeps saving settings"
print("test_console ok")
