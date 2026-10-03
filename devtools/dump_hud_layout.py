"""Dump the display tree of a HUD redswf: placements (name, matrix) and text field bounds.

usage: python devtools/dump_hud_layout.py [hud_dialog] [root_name]
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gamepath import game_path

from core.bundle import read_bundle
from core.swf_font import _Bits, _swf_body, _tags

BUNDLE = game_path("content", "content0", "bundles", "startup.bundle")


def inner_tags(d: bytes, p: int):
    while p + 2 <= len(d):
        code_len = struct.unpack_from("<H", d, p)[0]
        p += 2
        code, ln = code_len >> 6, code_len & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", d, p)[0]
            p += 4
        yield code, d[p:p + ln]
        p += ln
        if code == 0:
            break


def cstr(d: bytes, p: int):
    e = d.index(b"\0", p)
    return d[p:e].decode("latin-1"), e + 1


def matrix(b: _Bits):
    sx = sy = 1.0
    r0 = r1 = 0.0
    if b.u(1):
        n = b.u(5)
        sx, sy = b.s(n) / 65536, b.s(n) / 65536
    if b.u(1):
        n = b.u(5)
        r0, r1 = b.s(n) / 65536, b.s(n) / 65536
    n = b.u(5)
    tx, ty = b.s(n) / 20, b.s(n) / 20
    if b.bit:
        b.bit, b.pos = 0, b.pos + 1
    return sx, sy, r0, r1, tx, ty


def cxform(b: _Bits, alpha: bool):
    has_add, has_mult = b.u(1), b.u(1)
    n = b.u(4)
    for _ in range((4 if alpha else 3) * (has_add + has_mult)):
        b.s(n)
    if b.bit:
        b.bit, b.pos = 0, b.pos + 1


def place(code: int, d: bytes):
    try:
        return _place(code, d)
    except (struct.error, ValueError, IndexError):
        return dict(depth=-1, cid=None, name=f"<bad place {d.hex()}>", matrix=None, cls=None, move=False)


def _place(code: int, d: bytes):
    f = d[0]
    p = 1
    f2 = 0
    cls = None
    if code == 70:
        f2 = d[1]
        p = 2
    depth = struct.unpack_from("<H", d, p)[0]
    p += 2
    if code == 70 and (f2 & 0x08 or (f2 & 0x10 and f & 0x02)):
        cls, p = cstr(d, p)
    cid = None
    if f & 0x02:
        cid = struct.unpack_from("<H", d, p)[0]
        p += 2
    m = None
    b = _Bits(d, p)
    if f & 0x04:
        m = matrix(b)
    if f & 0x08:
        cxform(b, True)
    p = b.pos
    if f & 0x10:
        p += 2
    name = None
    if f & 0x20:
        name, p = cstr(d, p)
    return dict(depth=depth, cid=cid, name=name, matrix=m, cls=cls, move=bool(f & 1))


def edit_text(d: bytes):
    cid = struct.unpack_from("<H", d, 0)[0]
    b = _Bits(d, 2)
    n = b.u(5)
    xmin, xmax, ymin, ymax = (b.s(n) / 20 for _ in range(4))
    p = b.pos + (1 if b.bit else 0)
    f1, f2 = d[p], d[p + 1]
    p += 2
    info = dict(bounds=(xmin, ymin, xmax, ymax), wordwrap=bool(f1 & 0x40), multiline=bool(f1 & 0x20),
                autosize=bool(f2 & 0x40), html=bool(f2 & 0x02))
    if f1 & 0x01:
        p += 2
    if f2 & 0x80:
        _, p = cstr(d, p)
    if f1 & 0x01 or f2 & 0x80:
        info["height"] = struct.unpack_from("<H", d, p)[0] / 20
        p += 2
    if f1 & 0x04:
        p += 4
    if f1 & 0x02:
        p += 2
    if f2 & 0x20:
        info["align"] = ("left", "right", "center", "justify")[d[p]] if d[p] < 4 else d[p]
        p += 9
    info["var"], p = cstr(d, p)
    return cid, info


def main():
    want = (sys.argv[1] if len(sys.argv) > 1 else "hud_dialog") + ".redswf"
    root_name = sys.argv[2] if len(sys.argv) > 2 else None
    f = next(f for f in read_bundle(BUNDLE) if f.path.replace("\\", "/").endswith("hud/" + want))
    body = _swf_body(f.data)
    sprites: dict[int, list] = {}
    texts: dict[int, dict] = {}
    symbols: dict[int, str] = {}
    top: list = []
    for code, d in _tags(body):
        if code == 39:
            sid = struct.unpack_from("<H", d, 0)[0]
            sprites[sid] = [place(c, x) for c, x in inner_tags(d, 4) if c in (26, 70)]
        elif code == 37:
            cid, info = edit_text(d)
            texts[cid] = info
        elif code in (26, 70):
            top.append(place(code, d))
        elif code in (56, 76):
            n = struct.unpack_from("<H", d, 0)[0]
            p = 2
            for _ in range(n):
                cid = struct.unpack_from("<H", d, p)[0]
                name, p = cstr(d, p + 2)
                symbols[cid] = name

    def show(items, indent, seen):
        by_depth = {}
        for it in items:
            if it["cid"] is not None or it["depth"] not in by_depth:
                by_depth[it["depth"]] = it
        for it in sorted(by_depth.values(), key=lambda i: i["depth"]):
            cid = it["cid"]
            m = it["matrix"]
            pos = f"({m[4]:.1f},{m[5]:.1f}) s=({m[0]:.2f},{m[1]:.2f})" if m else "-"
            label = symbols.get(cid, "")
            extra = f" text {texts[cid]}" if cid in texts else ""
            print(f"{'  ' * indent}{it['name'] or '?'} cid={cid} {label} {pos}{extra}")
            if cid in sprites and cid not in seen:
                show(sprites[cid], indent + 1, seen | {cid})

    items = top
    if root_name:
        def find(items, seen):
            for it in items:
                if it["name"] == root_name:
                    return [it]
                if it["cid"] in sprites and it["cid"] not in seen:
                    r = find(sprites[it["cid"]], seen | {it["cid"]})
                    if r:
                        return r
            return None
        items = find(top, set()) or []
    show(items, 0, set())
    print("symbols:", {k: v for k, v in symbols.items() if "ption" in v or "ialog" in v or "ubtit" in v})


if __name__ == "__main__":
    main()
