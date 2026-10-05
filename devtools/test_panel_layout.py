import os, struct, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import game_path
from pathlib import Path
from core.bundle import iter_bundle
from core.logo import GUI_BUNDLE
from core.panel_layout import (ALIGN_JUSTIFY, PANELS, ROW_GAP, ROW_PANELS, STARTUP_BUNDLE, STARTUP_PANELS,
                               TOOLTIP_PANELS, _text_fields, panel_files, row_padding_sites, wanted_leading)

CONTENT0 = Path(game_path("content", "content0"))


def swf(data):
    at = data.find(b"CFX")
    return zlib.decompressobj().decompress(data[at + 8:])


def signed(b):
    return b - 256 if b > 127 else b


orig = {f.path: f.data for f in iter_bundle(CONTENT0 / "bundles" / GUI_BUNDLE, lambda n, _s: n.startswith(PANELS))}
orig.update({f.path: f.data for f in iter_bundle(CONTENT0 / "bundles" / STARTUP_BUNDLE,
                                                 lambda n, _s: n in STARTUP_PANELS)})
files = panel_files(CONTENT0)
names = sorted(f.path.rsplit("\\", 1)[-1] for f in files)
print(names)
for want in ("panel_glossary_bestiary.redswf", "panel_glossary_encyclopedia.redswf", "panel_glossary_main.redswf",
             "panel_glossary_storybook.redswf", "panel_glossary_books.redswf", "panel_journal_quests.redswf",
             "panel_overlay.redswf", "panel_noticeboard.redswf", "componentslib.redswf", "panel_common.redswf",
             "panel_inventory.redswf", "popup_tutorial.redswf", "loadingscreen.redswf",
             "panel_recapmovies.redswf", "panel_startupmovies.redswf", "hud_subtitles.redswf",
             "hud_dialog.redswf", "panel_character.redswf", "panel_loading_velen.redswf",
             "panel_loading_bob.redswf", "panel_loading_skellige.redswf"):
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
        want = wanted_leading(a, f.path in TOOLTIP_PANELS)
        if want is not None:
            assert lead >= want
            bodies += 1
        else:
            assert lead == struct.unpack_from("<h", before, a.align + 7)[0]
        if before[a.align:a.align + 9] != after[b.align:b.align + 9]:
            allowed.update(range(a.align, a.align + 9))
            allowed.update(range(a.text, a.text + a.text_len))
    rows = row_padding_sites(before) if f.path in ROW_PANELS else []
    for site in rows:
        assert signed(after[site]) == signed(before[site]) + ROW_GAP, (site, before[site], after[site])
    allowed.update(rows)
    diff = {i for i in range(len(before)) if before[i] != after[i]}
    assert diff and diff <= allowed, sorted(diff - allowed)[:5]
    print(f.path.rsplit("\\", 1)[-1], "bodies", bodies, "rows", [signed(before[s]) for s in rows],
          "changed bytes", len(diff))
assert any(row_padding_sites(swf(orig[p])) for p in orig if p in ROW_PANELS)
print("ok")
