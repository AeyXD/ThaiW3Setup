import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import game_path
from core.assets import font_bundle, font_files, storybook_files, write_mod_content
from core.bundle import read_bundle
from core.options import FONTS

meta = open(game_path("content", "metadata.store"), "rb").read()
names = set(meta.split(b"\0"))
tmp = Path(tempfile.mkdtemp())
for font in FONTS:
    all_files = read_bundle(font_bundle(font))
    files = font_files(font)
    out = tmp / font
    write_mod_content(out, files)
    back = read_bundle(out / "blob0.bundle")
    same = all(a.path == b.path and a.data == b.data for a, b in zip(files, back))
    print(font, [f.path for f in all_files], "roundtrip", same, (out / "blob0.bundle").stat().st_size,
          "in game", files[0].path.encode() in names)
for slot in ("tr", "en"):
    files = storybook_files(slot)
    write_mod_content(tmp / ("sb_" + slot), files)
    back = read_bundle(tmp / ("sb_" + slot) / "blob0.bundle")
    print("storybook", slot, len(back), all(a.data == b.data for a, b in zip(files, back)),
          sum(1 for f in back if f.path.encode() in names), "paths in game", back[0].path)
