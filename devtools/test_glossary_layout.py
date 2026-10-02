import os, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from core.bundle import iter_bundle
from core.glossary_layout import ALIGN_LEFT, GLOSSARY_DIR, _justified_fields, glossary_files
from core.logo import GUI_BUNDLE

CONTENT0 = Path(r"D:\SteamLibrary\steamapps\common\The Witcher 3\content\content0")


def swf(data):
    at = data.find(b"CFX")
    return zlib.decompressobj().decompress(data[at + 8:])


orig = {f.path: f.data for f in iter_bundle(CONTENT0 / "bundles" / GUI_BUNDLE, lambda n, _s: n.startswith(GLOSSARY_DIR))}
files = glossary_files(CONTENT0)
names = sorted(f.path.rsplit("\\", 1)[-1] for f in files)
print(names)
assert names == ["panel_glossary_bestiary.redswf", "panel_glossary_encyclopedia.redswf",
                 "panel_glossary_main.redswf", "panel_glossary_storybook.redswf"], names
for f in files:
    before, after = swf(orig[f.path]), swf(f.data)
    assert len(f.data) == len(orig[f.path])
    assert len(before) == len(after)
    assert not _justified_fields(after)
    allowed = set()
    for align, text, ln in _justified_fields(before):
        assert after[align] == ALIGN_LEFT
        allowed.add(align)
        allowed.update(range(text, text + ln))
    diff = {i for i in range(len(before)) if before[i] != after[i]}
    assert diff <= allowed, sorted(diff - allowed)[:5]
    print(f.path.rsplit("\\", 1)[-1], "changed bytes", len(diff))
print("ok")
