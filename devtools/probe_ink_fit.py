"""Disassemble inkFitOptions / logo layout that may place txtVersion."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.abc_patch import DO_ABC, _multiname_names, _u30, string_pool
from core.bundle import iter_bundle
from core.compat_text import _u30_bytes
from core.swf_font import _swf_body, _tags


def disasm(abc: bytes, names: list, strings: list, start: int, length: int = 200) -> None:
    op_label = {
        0x61: "set", 0x66: "get", 0x68: "init", 0x60: "getlex", 0x5D: "find",
        0x46: "call", 0x4F: "callvoid", 0x4A: "construct", 0x2C: "str",
    }
    p, end = start, min(len(abc), start + length)
    while p < end:
        opb = abc[p]
        at = p
        p += 1
        try:
            if opb == 0x24:
                print(f"  {at}: pushbyte {abc[p]}")
                p += 1
            elif opb == 0x25:
                v, p = _u30(abc, p)
                print(f"  {at}: pushshort {v}")
            elif opb == 0x2C:
                v, p = _u30(abc, p)
                print(f"  {at}: str {strings[v]!r}" if v < len(strings) else f"  {at}: str#{v}")
            elif opb in (0x61, 0x66, 0x68, 0x60, 0x5D):
                v, p = _u30(abc, p)
                print(f"  {at}: {op_label[opb]} {names[v] if v < len(names) else v}")
            elif opb in (0x46, 0x4F, 0x4A):
                v, p = _u30(abc, p)
                a, p = _u30(abc, p)
                print(f"  {at}: {op_label[opb]} {names[v] if v < len(names) else v}({a})")
            elif opb in (0xD0, 0xD1, 0xD2, 0xD3):
                print(f"  {at}: local_{opb - 0xD0}")
            elif opb == 0x62:
                v, p = _u30(abc, p)
                print(f"  {at}: getlocal {v}")
            elif opb == 0x63:
                v, p = _u30(abc, p)
                print(f"  {at}: setlocal {v}")
            elif opb == 0xA0:
                print(f"  {at}: add")
            elif opb == 0xA1:
                print(f"  {at}: sub")
            elif opb == 0xA2:
                print(f"  {at}: mul")
            elif opb == 0xA3:
                print(f"  {at}: div")
            elif opb == 0x47:
                print(f"  {at}: retvoid")
            elif opb == 0x10:
                print(f"  {at}: jump")
                p += 3
            elif opb in (0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18):
                print(f"  {at}: if_{opb:#x}")
                p += 3
            elif opb == 0x29:
                print(f"  {at}: pop")
            elif opb == 0x2A:
                print(f"  {at}: dup")
            elif opb == 0x26:
                print(f"  {at}: pushtrue")
            elif opb == 0x27:
                print(f"  {at}: pushfalse")
            else:
                print(f"  {at}: ?{opb:#x}")
        except Exception as exc:
            print(f"  {at}: ERR {exc}")
            break


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

    for prop in ("inkFitOptions", "inkLeftRule", "inkForged", "setVersion"):
        mns = [i for i, n in enumerate(names) if n == prop]
        print(f"=== {prop} mns={mns}")
        for mn in mns:
            for op in (0x4F, 0x46, 0x42, 0x4A, 0x68):
                start = 0
                while True:
                    j = abc.find(bytes([op]) + _u30_bytes(mn), start)
                    if j < 0:
                        break
                    print(f"call site @{j} op={op:#x}")
                    start = j + 1

    # method body of inkFitOptions: find trait name then surrounding
    # Instead: disasm from the call site backward to see args, and search for
    # setproperty x near strings / get textWidth in a wide window after inkFitOptions definition.
    # Find multiname inkFitOptions used as method name - look for debug name in metadata? 
    # Brute: any setproperty x within 300 bytes of getproperty txtVersion at 652437
    print("=== around txtVersion@652437 (inkFitOptions args) ===")
    disasm(abc, names, strings, 652400, 120)

    # Search method that contains both txtVersion get and set x
    txt_mn = next(i for i, n in enumerate(names) if n == "txtVersion")
    x_mns = {i for i, n in enumerate(names) if n == "x"}
    print("=== set x within 400 bytes of any txtVersion get ===")
    start = 0
    while True:
        j = abc.find(bytes([0x66]) + _u30_bytes(txt_mn), start)
        if j < 0:
            break
        for k in range(max(0, j - 50), min(len(abc) - 4, j + 400)):
            if abc[k] != 0x61:
                continue
            try:
                v, _ = _u30(abc, k + 1)
            except Exception:
                continue
            if v in x_mns:
                print(f"txtVersion@{j} -> set x @{k}")
                disasm(abc, names, strings, max(j, k - 40), 80)
        start = j + 1


if __name__ == "__main__":
    main()
