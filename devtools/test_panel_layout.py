import os, struct, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import game_path
from pathlib import Path
from core.bundle import iter_bundle
from core.logo import GUI_BUNDLE
from core.panel_layout import (ALIGN_JUSTIFY, BODY_LEADING, BODY_MIN_HEIGHT, PANELS, _text_fields,
                               panel_files)

CONTENT0 = Path(game_path("content", "content0"))


def swf(data):
    at = data.find(b"CFX")
    return zlib.decompressobj().decompress(data[at + 8:])


orig = {f.path: f.data for f in iter_bundle(CONTENT0 / "bundles" / GUI_BUNDLE, lambda n, _s: n.startswith(PANELS))}
files = panel_files(CONTENT0)
names = sorted(f.path.rsplit("\\", 1)[-1] for f in files)
print(names)
for want in ("panel_glossary_bestiary.redswf", "panel_glossary_encyclopedia.redswf", "panel_glossary_main.redswf",
             "panel_glossary_storybook.redswf", "panel_glossary_books.redswf", "panel_journal_quests.redswf",
             "panel_overlay.redswf", "panel_noticeboard.redswf"):
    assert want in names, want
for f in files:
    before, after = swf(orig[f.path]), swf(f.data)
    assert len(f.data) == len(orig[f.path])
    assert len(before) == len(after)
    allowed = set()
    bodies = 0
    for a, b in zip(_text_fields(before), _text_fields(after)):
        assert after[b.align] != ALIGN_JUSTIFY
        lead = struct.unpack_from("<h", after, b.align + 7)[0]
        if a.multiline and a.height >= BODY_MIN_HEIGHT:
            assert lead >= BODY_LEADING
            bodies += 1
        else:
            assert lead == struct.unpack_from("<h", before, a.align + 7)[0]
        if before[a.align:a.align + 9] != after[b.align:b.align + 9]:
            allowed.update(range(a.align, a.align + 9))
            allowed.update(range(a.text, a.text + a.text_len))
    diff = {i for i in range(len(before)) if before[i] != after[i]}
    assert diff and diff <= allowed, sorted(diff - allowed)[:5]
    print(f.path.rsplit("\\", 1)[-1], "bodies", bodies, "changed bytes", len(diff))
print("ok")
