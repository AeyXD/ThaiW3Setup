"""Probe whether mcModVersion x is set from ActionScript (near textWidth / title)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.abc_patch import DO_ABC, _multiname_names, _u30
from core.bundle import iter_bundle
from core.compat_text import _u30_bytes
from core.swf_font import _swf_body, _tags

TARGET = {
    "mcModVersion", "modVersion", "txtVersion", "x", "y", "width", "textWidth",
    "setVersion", "THE WITCHER", "tfTitle",
}


def main() -> None:
    bundle = Path(
        r"D:\SteamLibrary\steamapps\common\The Witcher 3\mods"
        r"\modInkAndIronUI\content\blob0.bundle"
    )
    menu = next(iter_bundle(bundle, lambda n, _: "panel_ingamemenu" in n))
    body = _swf_body(menu.data)
    abc = next(d for tag, d in _tags(body) if tag == DO_ABC)
    abc_at = abc.index(bytes([0]), 4) + 1
    names = _multiname_names(abc, abc_at)
    wanted: dict[str, list[int]] = {}
    for i, name in enumerate(names):
        if name in TARGET:
            wanted.setdefault(name, []).append(i)
    print("multiname idxs", {k: v[:8] for k, v in sorted(wanted.items())})

    def find_ops(mn_set: set[int], ops=(0x66, 0x61, 0x68, 0x4F, 0x46, 0x60, 0x5D)):
        hits = []
        for mn in mn_set:
            for op in ops:
                needle = bytes([op]) + _u30_bytes(mn)
                start = 0
                while True:
                    j = abc.find(needle, start)
                    if j < 0:
                        break
                    hits.append((j, op, mn))
                    start = j + 1
        return sorted(hits)

    ver_mns = set(wanted.get("mcModVersion", []) + wanted.get("txtVersion", []))
    x_mns = set(wanted.get("x", []))
    tw_mns = set(wanted.get("textWidth", []))
    ver_hits = find_ops(ver_mns)
    x_hits = find_ops(x_mns)
    tw_hits = find_ops(tw_mns)
    print("ver property ops", len(ver_hits))
    print("x property ops", len(x_hits))
    print("textWidth ops", len(tw_hits))

    interesting = []
    for j, op, mn in ver_hits:
        for xj, xop, xmn in x_hits:
            if abs(xj - j) < 120 and xop in (0x61, 0x68):
                interesting.append((j, op, mn, xj, xop, xmn))
    print("ver near set-x", len(interesting), interesting[:20])

    near_tw = [(j, tj) for j, op, mn in ver_hits for tj, top, tmn in tw_hits if abs(tj - j) < 160]
    print("ver near textWidth", len(near_tw), near_tw[:20])

    for j, op, mn in ver_hits[:20]:
        # disassemble a short window
        ops = []
        p = max(abc_at, j - 30)
        end = min(len(abc), j + 50)
        while p < end:
            opb = abc[p]
            start = p
            p += 1
            # rough: many ops have u30
            if opb in (0x24,):  # pushbyte
                ops.append((start, f"pushbyte {abc[p]}"))
                p += 1
            elif opb in (0x25,):
                v, p = _u30(abc, p)
                ops.append((start, f"pushshort {v}"))
            elif opb in (0x2C, 0x2D, 0x2E, 0x40, 0x41, 0x42, 0x43, 0x45, 0x46, 0x49, 0x4A, 0x4E, 0x4F,
                         0x5D, 0x5E, 0x60, 0x61, 0x66, 0x68, 0x80, 0x86):
                v, p = _u30(abc, p)
                argc = None
                if opb in (0x41, 0x42, 0x43, 0x45, 0x46, 0x49, 0x4A, 0x4E, 0x4F):
                    argc, p = _u30(abc, p)
                label = {0x2C: "pushstring", 0x46: "callproperty", 0x4F: "callpropvoid",
                         0x5D: "findpropstrict", 0x60: "getlex", 0x61: "setproperty",
                         0x66: "getproperty", 0x68: "initproperty"}.get(opb, hex(opb))
                nm = names[v] if v < len(names) else None
                ops.append((start, f"{label} {v}({nm}) argc={argc}"))
            elif opb in (0xD0, 0xD1, 0xD2, 0xD3):
                ops.append((start, f"getlocal_{opb - 0xD0}"))
            elif opb in (0xD4, 0xD5, 0xD6, 0xD7):
                ops.append((start, f"setlocal_{opb - 0xD4}"))
            elif opb in (0xA0, 0xA1, 0xA2):
                ops.append((start, {0xA0: "add", 0xA1: "subtract", 0xA2: "multiply"}[opb]))
            elif opb in (0x47, 0x48, 0x29, 0x2A):
                ops.append((start, {0x47: "returnvoid", 0x48: "returnvalue", 0x29: "pop", 0x2A: "dup"}[opb]))
            else:
                ops.append((start, f"?{opb:#x}"))
        print(f"\n--- site @{j} ---")
        for at, text in ops:
            mark = " <<" if at == j else ""
            print(f"  {at}: {text}{mark}")


if __name__ == "__main__":
    main()
