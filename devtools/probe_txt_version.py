"""Trace txtVersion accesses and any x/y assignment."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.abc_patch import DO_ABC, _multiname_names, _u30, string_pool
from core.bundle import iter_bundle
from core.compat_text import _u30_bytes
from core.swf_font import _swf_body, _tags


def main() -> None:
    bundle = Path(
        r"D:\SteamLibrary\steamapps\common\The Witcher 3\mods"
        r"\modInkAndIronUI\content\blob0.bundle"
    )
    menu = next(iter_bundle(bundle, lambda n, _: "panel_ingamemenu" in n))
    body = _swf_body(menu.data)
    abc = next(d for t, d in _tags(body) if t == DO_ABC)
    abc_at = abc.index(bytes([0]), 4) + 1
    names = _multiname_names(abc, abc_at)
    _, spans, _ = string_pool(abc, abc_at)
    strings = [""] + [abc[a:b].decode("utf-8", "replace") for a, b in spans]

    op_label = {0x61: "set", 0x66: "get", 0x68: "init", 0x60: "getlex", 0x5D: "find"}
    for prop in ("txtVersion", "mcModVersion", "inkArt"):
        mns = [i for i, n in enumerate(names) if n == prop]
        print(f"=== {prop} mns={mns}")
        for mn in mns:
            start = 0
            while True:
                j = abc.find(bytes([0x66]) + _u30_bytes(mn), start)
                if j < 0:
                    break
                ops = []
                p = j
                for _ in range(14):
                    if p >= len(abc):
                        break
                    opb = abc[p]
                    p += 1
                    if opb == 0x24:
                        ops.append(f"pushbyte({abc[p]})")
                        p += 1
                    elif opb == 0x25:
                        v, p = _u30(abc, p)
                        ops.append(f"pushshort({v})")
                    elif opb in op_label:
                        v, p = _u30(abc, p)
                        nm = names[v] if v < len(names) else v
                        ops.append(f"{op_label[opb]}:{nm}")
                    elif opb == 0x2C:
                        v, p = _u30(abc, p)
                        ops.append(f"str:{strings[v]!r}" if v < len(strings) else f"str#{v}")
                    elif opb in (0xD0, 0xD1, 0xD2, 0xD3):
                        ops.append(f"local_{opb - 0xD0}")
                    elif opb == 0x4F:
                        v, p = _u30(abc, p)
                        a, p = _u30(abc, p)
                        ops.append(f"callvoid:{names[v]}({a})")
                    elif opb == 0x46:
                        v, p = _u30(abc, p)
                        a, p = _u30(abc, p)
                        ops.append(f"call:{names[v]}({a})")
                    elif opb == 0xA0:
                        ops.append("add")
                    elif opb == 0xA1:
                        ops.append("sub")
                    elif opb == 0x12:
                        ops.append("iffalse")
                        p += 3
                    elif opb == 0x47:
                        ops.append("retvoid")
                        break
                    else:
                        ops.append(hex(opb))
                print(f"@{j}", " | ".join(ops))
                start = j + 1

    # also search inkTf args that might include version: look for getproperty version / _version near inkArt block
    print("=== strings around logo block containing digits or version ===")
    for i, s in enumerate(strings):
        if s in ("v5.01", "5.01", "v", "version", "Version") or (s.startswith("v") and any(c.isdigit() for c in s)):
            print(i, repr(s))


if __name__ == "__main__":
    main()
