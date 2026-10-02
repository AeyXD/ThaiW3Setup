"""Thai game logo for the main menu and the press-any-key screen.

Each menu .redswf embeds texture atlases, and its logo sprite shows a sub-image of one of them picked by a
frame label named after the text language. Thai rides on the English or Turkish slot, whose frames are EN
and REST, so the logo is swapped by redrawing that sub-image. The files are read from the player's own
game at install time, so a game patch never leaves an outdated copy of the menus in mods.
"""
from __future__ import annotations

import io
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from .bundle import BundleFile, iter_bundle
from .paths import assets_dir
from .progress import ProgressFn, noop
from .swf_font import _Bits, _swf_body, _tags

GUI_BUNDLE = "r4gui.bundle"
MENU_FILES = (
    "gameplay\\gui_new\\swf\\mainmenu\\panel_ingamemenu.redswf",
    "gameplay\\gui_new\\swf\\startscreen\\panel_startscreen.redswf",
    "gameplay\\gui_new\\swf\\startscreen\\panel_startscreen_ep1.redswf",
    "gameplay\\gui_new\\swf\\startscreen\\panel_startscreen_ep2.redswf",
)
LOGO_FRAMES = {"EN", "REST"}
# mcGameLogo / mcGameLogoRE in the main menu, GameLogo on the start screen; EP1Logo / EP2Logo are DLC banners
LOGO_SYMBOL = "GameLogo"
DXT5 = "TCM_DXTAlpha"
# the CR2W header CRC is taken with this value in its own slot
HEADER_CRC_SEED = 0xDEADBEEF
HEADER_SIZE = 160
TEXTURE_HEADER = struct.Struct("<7I")


class LogoError(Exception):
    pass


def logo_image() -> Path:
    return assets_dir() / "logo" / "thai_logo.png"


@dataclass
class _Export:
    index: int
    cls: str
    offset: int
    size: int
    props: dict[str, bytes]
    props_end: int


@dataclass
class _Cr2w:
    names: list[str]
    tables: list[tuple[int, int, int]]
    exports: list[_Export]


def _read_cr2w(data: bytes) -> _Cr2w:
    if data[:4] != b"CR2W":
        raise LogoError("not a CR2W file")
    tables = [struct.unpack_from("<III", data, 40 + i * 12) for i in range(10)]
    str_off, str_len, _ = tables[0]
    strings = data[str_off:str_off + str_len]
    names = []
    for i in range(tables[1][1]):
        o = struct.unpack_from("<I", data, tables[1][0] + i * 8)[0]
        names.append(strings[o:strings.index(b"\0", o)].decode("latin-1"))
    exports = []
    for i in range(tables[4][1]):
        cls, _flags, _parent, size, offset = struct.unpack_from("<HHIII", data, tables[4][0] + i * 24)
        props, p = {}, offset + 1
        while True:
            name = struct.unpack_from("<H", data, p)[0]
            if name == 0:
                p += 2
                break
            ln = struct.unpack_from("<I", data, p + 4)[0]
            props[names[name]] = data[p + 8:p + 4 + ln]
            p += 4 + ln
        exports.append(_Export(i, names[cls], offset, size, props, p))
    return _Cr2w(names, tables, exports)


def _rect_len(d: bytes, p: int) -> int:
    return (5 + 4 * (d[p] >> 3) + 7) // 8


def _matrix_len(d: bytes, p: int) -> int:
    b = _Bits(d, p)
    for _ in range(2):
        if b.u(1):
            n = b.u(5)
            b.u(2 * n)
    n = b.u(5)
    b.u(2 * n)
    return b.pos - p + (1 if b.bit else 0)


def _shape_bitmaps(code: int, d: bytes) -> list[int]:
    """Bitmap ids in the fill style table of a DefineShape 1-4 tag."""
    p = 2 + _rect_len(d, 2)
    if code == 83:
        p += _rect_len(d, p) + 1
    n = d[p]
    p += 1
    if n == 0xFF:
        n = struct.unpack_from("<H", d, p)[0]
        p += 2
    rgba = code not in (2, 22)
    out = []
    for _ in range(n):
        kind = d[p]
        p += 1
        if kind == 0x00:
            p += 4 if rgba else 3
        elif kind in (0x10, 0x12, 0x13):
            p += _matrix_len(d, p)
            p += 1 + (d[p] & 15) * (5 if rgba else 4)
            if kind == 0x13:
                p += 2
        elif 0x40 <= kind <= 0x43:
            out.append(struct.unpack_from("<H", d, p)[0])
            p += 2
            p += _matrix_len(d, p)
        else:
            raise LogoError(f"unknown fill style {kind:#x}")
    return out


def _sprite_tags(raw: bytes):
    p = 0
    while p + 2 <= len(raw):
        code_len = struct.unpack_from("<H", raw, p)[0]
        p += 2
        code, ln = code_len >> 6, code_len & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", raw, p)[0]
            p += 4
        yield code, raw[p:p + ln]
        p += ln
        if code == 0:
            break


def _placed_char(code: int, d: bytes) -> int | None:
    flags = d[0]
    if not flags & 2:
        return None
    p = 3
    if code == 70:
        p = 4
        if d[1] & 8:
            p = d.index(b"\0", p) + 1
    return struct.unpack_from("<H", d, p)[0]


def _logo_regions(swf: bytes) -> list[tuple[str, tuple[int, int, int, int]]]:
    """(atlas file name, x1 y1 x2 y2) of every sub-image the game logo sprites show for the EN and REST frames."""
    images, subs, shapes, sprites, symbols = {}, {}, {}, {}, {}
    for code, d in _tags(swf):
        if code == 1009:
            p = 10
            p += 1 + d[p]
            images[struct.unpack_from("<I", d, 0)[0] & 0xFFFF] = d[p + 1:p + 1 + d[p]].decode("latin-1")
        elif code == 1008:
            cid, image, *rect = struct.unpack_from("<6H", d, 0)
            subs[cid] = (image, tuple(rect))
        elif code in (2, 22, 32, 83):
            shapes[struct.unpack_from("<H", d, 0)[0]] = _shape_bitmaps(code, d)
        elif code == 39:
            sprites[struct.unpack_from("<H", d, 0)[0]] = d[4:]
        elif code == 76:
            p = 2
            for _ in range(struct.unpack_from("<H", d, 0)[0]):
                end = d.index(b"\0", p + 2)
                symbols[struct.unpack_from("<H", d, p)[0]] = d[p + 2:end].decode("latin-1")
                p = end + 1
    found = []
    for sid, raw in sprites.items():
        if LOGO_SYMBOL not in symbols.get(sid, ""):
            continue
        label = None
        for code, d in _sprite_tags(raw):
            if code == 43:
                label = d.split(b"\0")[0].decode("latin-1")
            elif code == 1:
                label = None
            elif code in (26, 70) and label in LOGO_FRAMES:
                for bitmap in shapes.get(_placed_char(code, d), []):
                    if bitmap in subs and subs[bitmap][0] in images:
                        image, rect = subs[bitmap]
                        found.append((images[image], rect))
    return sorted(set(found))


def _dds(width: int, height: int, blocks: bytes) -> bytes:
    header = struct.pack("<4sIIIIIII44xII4sIIIII", b"DDS ", 124, 0x81007, height, width, len(blocks), 0, 1,
                         32, 4, b"DXT5", 0, 0, 0, 0, 0)
    return header + struct.pack("<IIIII", 0x1000, 0, 0, 0, 0) + blocks


def _decode_dxt5(blocks: bytes, width: int, height: int):
    from PIL import Image

    img = Image.open(io.BytesIO(_dds(width, height, blocks)))
    img.load()
    return img.convert("RGBA")


def _encode_dxt5(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "DDS", pixel_format="DXT5")
    data = buf.getvalue()
    if data[84:88] != b"DXT5":
        raise LogoError("DXT5 encoder wrote an unexpected header")
    return data[128:]


def _draw_logo(region, rect: tuple[int, int, int, int], logo) -> None:
    """Replace the old logo inside rect (relative to region) with logo at the old logo's height and centre."""
    from PIL import Image

    x1, y1, x2, y2 = rect
    old = region.crop(rect).getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    bx1, by1, bx2, by2 = old or (0, 0, x2 - x1, y2 - y1)
    scale = min((by2 - by1) / logo.height, (x2 - x1) / logo.width, (y2 - y1) / logo.height)
    size = (max(1, round(logo.width * scale)), max(1, round(logo.height * scale)))
    fitted = logo.resize(size, Image.LANCZOS)
    left = min(max(x1 + (bx1 + bx2 - size[0]) // 2, x1), x2 - size[0])
    top = min(max(y1 + (by1 + by2 - size[1]) // 2, y1), y2 - size[1])
    region.paste((0, 0, 0, 0), rect)
    layer = Image.new("RGBA", region.size, (0, 0, 0, 0))
    layer.paste(fitted, (left, top))
    region.alpha_composite(layer)


def _patch_texture(data: bytearray, exp: _Export, cr2w: _Cr2w, rect: tuple[int, int, int, int], logo) -> None:
    compression = cr2w.names[struct.unpack("<H", exp.props["compression"])[0]] if "compression" in exp.props else ""
    width = struct.unpack("<I", exp.props["width"])[0]
    height = struct.unpack("<I", exp.props["height"])[0]
    _unk, mips, w, h, _pitch, size, _ = TEXTURE_HEADER.unpack_from(data, exp.props_end)
    bw, bh = (width + 3) // 4, (height + 3) // 4
    if compression != DXT5 or mips != 1 or (w, h) != (width, height) or size != bw * bh * 16:
        raise LogoError(f"unsupported logo texture {compression} {width}x{height} mips={mips}")
    pixels = exp.props_end + TEXTURE_HEADER.size
    x1, y1, x2, y2 = rect
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise LogoError(f"logo region {rect} outside the {width}x{height} texture")
    cx1, cy1, cx2, cy2 = x1 // 4, y1 // 4, (x2 + 3) // 4, (y2 + 3) // 4
    row_len = (cx2 - cx1) * 16
    rows = [pixels + (by * bw + cx1) * 16 for by in range(cy1, cy2)]
    blocks = b"".join(bytes(data[o:o + row_len]) for o in rows)
    region = _decode_dxt5(blocks, (cx2 - cx1) * 4, (cy2 - cy1) * 4)
    _draw_logo(region, (x1 - cx1 * 4, y1 - cy1 * 4, x2 - cx1 * 4, y2 - cy1 * 4), logo)
    encoded = _encode_dxt5(region)
    if len(encoded) != len(blocks):
        raise LogoError("re-encoded logo has a different size")
    for i, o in enumerate(rows):
        data[o:o + row_len] = encoded[i * row_len:(i + 1) * row_len]


def _fix_crcs(data: bytearray, cr2w: _Cr2w, changed: set[int]) -> None:
    table_off, count, _ = cr2w.tables[4]
    for exp in cr2w.exports:
        if exp.index in changed:
            struct.pack_into("<I", data, table_off + exp.index * 24 + 20,
                             zlib.crc32(data[exp.offset:exp.offset + exp.size]))
    struct.pack_into("<I", data, 40 + 4 * 12 + 8, zlib.crc32(data[table_off:table_off + count * 24]))
    struct.pack_into("<I", data, 32, HEADER_CRC_SEED)
    struct.pack_into("<I", data, 32, zlib.crc32(data[:HEADER_SIZE]))


def patch_menu(data: bytes, logo) -> bytes:
    """A menu .redswf with the EN/REST logo redrawn; logo is an RGBA image cropped to its content."""
    cr2w = _read_cr2w(data)
    resource = next((e for e in cr2w.exports if e.cls == "CSwfResource"), None)
    if resource is None:
        raise LogoError("no CSwfResource")
    regions = _logo_regions(_swf_body(data[resource.props_end:resource.offset + resource.size]))
    if not regions:
        raise LogoError("logo sprite not found")
    textures = [e for e in cr2w.exports if e.cls == "CSwfTexture"]
    out = bytearray(data)
    changed = set()
    for name, rect in regions:
        exp = next((e for e in textures if e.props.get("linkageName", b"").endswith(name.encode("latin-1"))), None)
        if exp is None:
            raise LogoError(f"texture {name} not found")
        _patch_texture(out, exp, cr2w, rect, logo)
        changed.add(exp.index)
    _fix_crcs(out, cr2w, changed)
    return bytes(out)


def load_logo(path: Path | None = None):
    from PIL import Image

    img = Image.open(path or logo_image()).convert("RGBA")
    box = img.getchannel("A").getbbox()
    if box is None:
        raise LogoError("logo image is empty")
    return img.crop(box)


def logo_files(content0: Path, progress: ProgressFn = noop) -> list[BundleFile]:
    """The menu files of the game with the Thai logo, ready for a mod bundle."""
    logo = load_logo()
    files = []
    for f in iter_bundle(content0 / "bundles" / GUI_BUNDLE, lambda n, _s: n in MENU_FILES):
        progress(len(files) / len(MENU_FILES), f"ใส่โลโก้ภาษาไทย {f.path.rsplit(chr(92), 1)[-1]}...")
        files.append(BundleFile(f.path, patch_menu(f.data, logo)))
    missing = set(MENU_FILES) - {f.path for f in files}
    if missing:
        raise LogoError(f"menu files missing from {GUI_BUNDLE}: {', '.join(sorted(missing))}")
    return files
