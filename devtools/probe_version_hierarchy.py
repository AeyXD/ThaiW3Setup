"""Map which sprites contain mcModVersion / txtVersion and where they are placed."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bundle import iter_bundle
from core.compat_text import _parse_place_matrix
from core.swf_font import _swf_body

NAMES = (b"mcModVersion\0", b"txtVersion\0", b"mcGameLogo\0", b"mcGameLogoRE\0")


def main() -> None:
    bundle = Path(
        r"D:\SteamLibrary\steamapps\common\The Witcher 3\mods"
        r"\modInkAndIronUI\content\blob0.bundle"
    )
    menu = next(iter_bundle(bundle, lambda n, _: "panel_ingamemenu" in n))
    body = _swf_body(menu.data)

    placements: list[tuple] = []
    sprite_kids: dict[object, list] = {}

    def walk(data: bytes, parent, root: bool = True) -> None:
        if root:
            nbits = data[0] >> 3
            p = (5 + 4 * nbits + 7) // 8 + 4
        else:
            p = 0
        while p + 2 <= len(data):
            code_len = struct.unpack_from("<H", data, p)[0]
            tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
            if ln == 0x3F:
                ln = struct.unpack_from("<I", data, hp)[0]
                hp += 4
            payload = data[hp : hp + ln]
            if tag == 39 and len(payload) >= 4:
                sid = struct.unpack_from("<H", payload, 0)[0]
                walk(payload[4:], sid, False)
            elif tag == 26:
                flags = payload[0]
                char = struct.unpack_from("<H", payload, 3)[0] if flags & 0x02 else None
                name = next((nm[:-1].decode() for nm in NAMES if nm in payload), None)
                parsed = _parse_place_matrix(payload) if flags & 0x04 else None
                tx, ty = (parsed[2], parsed[3]) if parsed else (None, None)
                if name:
                    placements.append((parent, char, name, tx, ty))
                    sprite_kids.setdefault(parent, []).append((name, tx, ty, char))
            p = hp + ln
            if tag == 0:
                break

    walk(body, "root")
    print("named placements:")
    for pl in placements:
        print(pl)
    print("sprites that contain version clips:")
    for sid, kids in sprite_kids.items():
        if any(k[0] in ("mcModVersion", "txtVersion") for k in kids):
            print("sprite", sid, kids)
            for parent, char, name, tx, ty in placements:
                if char == sid:
                    print("  placed as", name, "at", (tx, ty), "by parent", parent)


if __name__ == "__main__":
    main()
