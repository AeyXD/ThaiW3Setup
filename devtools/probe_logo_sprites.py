"""List sprites with EN/REST frame labels in a menu .redswf, with their labels and symbol names."""
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME
from core.bundle import iter_bundle  # noqa: E402
from core.logo import GUI_BUNDLE, _read_cr2w, _sprite_tags, _swf_body, _tags  # noqa: E402

GAME = Path(GAME)
target = sys.argv[1] if len(sys.argv) > 1 else "gameplay\\gui_new\\swf\\mainmenu\\panel_ingamemenu.redswf"
data = next(iter_bundle(GAME / "content" / "content0" / "bundles" / GUI_BUNDLE, lambda n, _s: n == target)).data
cr2w = _read_cr2w(data)
res = next(e for e in cr2w.exports if e.cls == "CSwfResource")
swf = _swf_body(data[res.props_end:res.offset + res.size])
symbols, sprites = {}, {}
for code, d in _tags(swf):
    if code == 76:
        p = 2
        for _ in range(struct.unpack_from("<H", d, 0)[0]):
            cid = struct.unpack_from("<H", d, p)[0]
            end = d.index(b"\0", p + 2)
            symbols[cid] = d[p + 2:end].decode("latin-1")
            p = end + 1
    elif code == 39:
        sprites[struct.unpack_from("<H", d, 0)[0]] = d[4:]
parents = {}
for sid, raw in sprites.items():
    for code, d in _sprite_tags(raw):
        if code in (26, 70) and d[0] & 2:
            p = 3 if code == 26 else 4
            parents.setdefault(struct.unpack_from("<H", d, p)[0], set()).add(sid)
for sid, raw in sprites.items():
    labels = [d.split(b"\0")[0].decode("latin-1") for code, d in _sprite_tags(raw) if code == 43]
    if "EN" in labels or "REST" in labels:
        print(sid, symbols.get(sid, ""), labels, "parents", sorted(parents.get(sid, ())),
              [symbols.get(p, "") for p in parents.get(sid, ())])
