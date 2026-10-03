"""Patch the menu logos from the installed game and save before/after crops to %TEMP%/w3thai_logo."""
import os
import tempfile
import struct
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME
from core.bundle import iter_bundle  # noqa: E402
from core.logo import (GUI_BUNDLE, MENU_FILES, _decode_dxt5, _logo_regions, _read_cr2w, _swf_body,  # noqa: E402
                       load_logo, logo_files, patch_menu)

GAME = Path(sys.argv[1] if len(sys.argv) > 1 else GAME)
OUT = Path(tempfile.gettempdir()) / "w3thai_logo"
OUT.mkdir(parents=True, exist_ok=True)
content0 = GAME / "content" / "content0"


def texture_image(data: bytes, name: str):
    cr2w = _read_cr2w(data)
    exp = next(e for e in cr2w.exports if e.cls == "CSwfTexture" and e.props["linkageName"].endswith(name.encode()))
    w = struct.unpack("<I", exp.props["width"])[0]
    h = struct.unpack("<I", exp.props["height"])[0]
    size = struct.unpack_from("<I", data, exp.props_end + 20)[0]
    return _decode_dxt5(data[exp.props_end + 28:exp.props_end + 28 + size], (w + 3) // 4 * 4, (h + 3) // 4 * 4)


def check_crcs(data: bytes) -> bool:
    cr2w = _read_cr2w(data)
    off, count, crc = cr2w.tables[4]
    ok = zlib.crc32(data[off:off + count * 24]) == crc
    for e in cr2w.exports:
        ok &= struct.unpack_from("<I", data, off + e.index * 24 + 20)[0] == zlib.crc32(data[e.offset:e.offset + e.size])
    head = bytearray(data[:160])
    struct.pack_into("<I", head, 32, 0xDEADBEEF)
    return ok and zlib.crc32(head) == struct.unpack_from("<I", data, 32)[0]


originals = {f.path: f.data for f in iter_bundle(content0 / "bundles" / GUI_BUNDLE, lambda n, _s: n in MENU_FILES)}
logo = load_logo()
for path, data in originals.items():
    cr2w = _read_cr2w(data)
    res = next(e for e in cr2w.exports if e.cls == "CSwfResource")
    regions = _logo_regions(_swf_body(data[res.props_end:res.offset + res.size]))
    t = time.time()
    patched = patch_menu(data, logo)
    stem = path.rsplit("\\", 1)[-1].replace(".redswf", "")
    print(stem, "regions", regions, f"{time.time() - t:.2f}s", "same size", len(patched) == len(data),
          "crc ok (orig, patched)", check_crcs(data), check_crcs(patched),
          "changed bytes", sum(1 for a, b in zip(data, patched) if a != b) if len(data) < 5_000_000 else "-")
    for i, (name, rect) in enumerate(regions):
        before = texture_image(data, name).crop(rect)
        after = texture_image(patched, name).crop(rect)
        for tag, im in (("before", before), ("after", after)):
            im.save(OUT / f"{stem}_{i}_{tag}.png")
        full = texture_image(patched, name)
        full.thumbnail((512, 512))
        full.save(OUT / f"{stem}_{i}_atlas.png")

t = time.time()
files = logo_files(content0)
print("logo_files", [f.path for f in files], f"{time.time() - t:.2f}s")
