"""Minimal DefineFont3 reader and renderer used for live subtitle previews."""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

EM = 1024 * 20  # DefineFont3 glyph units per em


class _Bits:
    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.pos, self.bit = data, pos, 0

    def u(self, n: int) -> int:
        v = 0
        for _ in range(n):
            byte = self.data[self.pos]
            v = (v << 1) | ((byte >> (7 - self.bit)) & 1)
            self.bit += 1
            if self.bit == 8:
                self.bit, self.pos = 0, self.pos + 1
        return v

    def s(self, n: int) -> int:
        v = self.u(n)
        return v - (1 << n) if n and v & (1 << (n - 1)) else v


def _parse_shape(data: bytes, steps: int = 6) -> list[list[tuple[float, float]]]:
    b = _Bits(data)
    fill_bits, line_bits = b.u(4), b.u(4)
    contours: list[list[tuple[float, float]]] = []
    x = y = 0
    cur: list[tuple[float, float]] = []
    while True:
        if b.u(1) == 0:
            flags = b.u(5)
            if flags == 0:
                break
            if flags & 1:
                n = b.u(5)
                x, y = b.s(n), b.s(n)
                if len(cur) > 2:
                    contours.append(cur)
                cur = [(x, y)]
            if flags & 2:
                b.u(fill_bits)
            if flags & 4:
                b.u(fill_bits)
            if flags & 8:
                b.u(line_bits)
            if flags & 16:
                break  # new styles never appear in font glyphs
            continue
        if not cur:
            cur = [(x, y)]
        if b.u(1):  # straight
            n = b.u(4) + 2
            if b.u(1):
                x += b.s(n)
                y += b.s(n)
            elif b.u(1):
                y += b.s(n)
            else:
                x += b.s(n)
            cur.append((x, y))
        else:
            n = b.u(4) + 2
            cx, cy = x + b.s(n), y + b.s(n)
            ax, ay = cx + b.s(n), cy + b.s(n)
            for i in range(1, steps + 1):
                t = i / steps
                mt = 1 - t
                cur.append((mt * mt * x + 2 * mt * t * cx + t * t * ax,
                            mt * mt * y + 2 * mt * t * cy + t * t * ay))
            x, y = ax, ay
    if len(cur) > 2:
        contours.append(cur)
    return contours


@dataclass
class Font:
    name: str
    ascent: int
    descent: int
    glyphs: dict[int, int] = field(default_factory=dict)  # char code -> glyph index
    shapes: list[bytes] = field(default_factory=list)
    advances: list[int] = field(default_factory=list)
    _cache: dict[int, list] = field(default_factory=dict, repr=False)

    def contours(self, index: int):
        if index not in self._cache:
            self._cache[index] = _parse_shape(self.shapes[index])
        return self._cache[index]


def _swf_body(data: bytes) -> bytes:
    for sig in (b"CFX", b"CWS", b"GFX", b"FWS"):
        i = data.find(sig)
        while i >= 0:
            if 5 <= data[i + 3] <= 40:
                body = data[i + 8:]
                if sig in (b"CWS", b"CFX"):
                    try:
                        body = zlib.decompressobj().decompress(body)
                    except zlib.error:
                        i = data.find(sig, i + 1)
                        continue
                return body
            i = data.find(sig, i + 1)
    raise ValueError("no SWF data")


def _tags(body: bytes):
    nbits = body[0] >> 3
    p = (5 + 4 * nbits + 7) // 8 + 4
    while p + 2 <= len(body):
        code_len = struct.unpack_from("<H", body, p)[0]
        p += 2
        code, ln = code_len >> 6, code_len & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, p)[0]
            p += 4
        yield code, body[p:p + ln]
        p += ln
        if code == 0:
            break


def _define_font3(d: bytes) -> Font:
    flags, nl = d[2], d[4]
    name = d[5:5 + nl].split(b"\0")[0].decode("latin-1")
    p = 5 + nl
    n = struct.unpack_from("<H", d, p)[0]
    p += 2
    table = p
    wide = flags & 0x08
    fmt, size = ("<I", 4) if wide else ("<H", 2)
    offsets = [struct.unpack_from(fmt, d, table + i * size)[0] for i in range(n + 1)]
    shapes = [d[table + offsets[i]:table + offsets[i + 1]] for i in range(n)]
    p = table + offsets[n]
    if flags & 0x04:
        codes = struct.unpack_from(f"<{n}H", d, p)
        p += 2 * n
    else:
        codes = tuple(d[p:p + n])
        p += n
    ascent = descent = 0
    advances = [EM // 2] * n
    if flags & 0x80:
        ascent, descent, _leading = struct.unpack_from("<hhh", d, p)
        p += 6
        advances = list(struct.unpack_from(f"<{n}h", d, p))
    return Font(name, ascent, descent, {c: i for i, c in enumerate(codes)}, shapes, advances)


def load_fonts(redswf: bytes) -> list[Font]:
    return [_define_font3(d) for code, d in _tags(_swf_body(redswf)) if code == 75]


def best_font(fonts: list[Font], sample: str) -> Font:
    return max(fonts, key=lambda f: (sum(1 for c in sample if ord(c) in f.glyphs), len(f.glyphs)))


def text_width(font: Font, text: str, px: int) -> float:
    return sum(font.advances[font.glyphs[ord(c)]] if ord(c) in font.glyphs else EM // 3 for c in text) * px / EM


def render_line(font: Font, text: str, px: int, color: tuple[int, int, int], scale: int = 3):
    """Render text as an RGBA Pillow image; px is the font size in pixels."""
    from PIL import Image, ImageChops, ImageDraw

    k = px * scale / EM
    asc = font.ascent or int(EM * 0.9)
    desc = font.descent or int(EM * 0.3)
    width = sum(font.advances[font.glyphs[ord(c)]] if ord(c) in font.glyphs else EM // 3 for c in text)
    # Thai upper vowels and tone marks stack above the font ascent.
    head = EM // 2
    w, h = max(1, int(width * k) + px * scale // 3), max(1, int((head + asc + desc) * k) + 2 * scale)
    mask = Image.new("1", (w, h), 0)
    pen = 2 * scale / k
    for c in text:
        gi = font.glyphs.get(ord(c))
        if gi is None:
            pen += EM // 3
            continue
        glyph = Image.new("1", (w, h), 0)
        draw = ImageDraw.Draw(glyph)
        for contour in font.contours(gi):
            part = Image.new("1", (w, h), 0)
            ImageDraw.Draw(part).polygon([((pen + x) * k, (head + asc + y) * k + scale) for x, y in contour], fill=1)
            glyph = ImageChops.logical_xor(glyph, part)
        del draw
        mask = ImageChops.logical_or(mask, glyph)
        pen += font.advances[gi]
    bbox = mask.getbbox()
    top = min(bbox[1] if bbox else h, int(head * k)) // scale * scale
    mask = mask.crop((0, top, w, h))
    w, h = mask.size
    alpha = mask.convert("L").resize((max(1, w // scale), max(1, h // scale)), Image.LANCZOS)
    img = Image.new("RGBA", alpha.size, color + (0,))
    img.putalpha(alpha)
    return img


EMPTY_SHAPE = b"\x10\x00"  # one fill bit, no line bits, end-of-shape record
EMPTY_RECT = b"\x00"
# CR2W wrapper of fonts_en.redswf: u32 sizes that move with the embedded SWF
CR2W_FILE_SIZES = (24, 28)
CR2W_EXPORT_SIZE = 385
CR2W_SWF_SIZE = 597


def _rect_len(data: bytes, pos: int) -> int:
    return (5 + 4 * (data[pos] >> 3) + 7) // 8


@dataclass
class _Font3:
    head: bytes
    flags: int
    codes: list[int]
    shapes: list[bytes]
    metrics: bytes
    advances: list[int]
    bounds: list[bytes]
    kerning: bytes

    def put(self, code: int, shape: bytes, advance: int, bounds: bytes) -> None:
        """Set the glyph of code, inserting it in code order when the font lacks it."""
        if code in self.codes:
            at = self.codes.index(code)
        else:
            at = next((i for i, c in enumerate(self.codes) if c > code), len(self.codes))
            for seq, value in ((self.codes, code), (self.shapes, b""), (self.advances, 0), (self.bounds, b"")):
                seq.insert(at, value)
        self.shapes[at] = shape
        if self.flags & 0x80:
            self.advances[at], self.bounds[at] = advance, bounds

    def glyph(self, code: int) -> tuple[bytes, int, bytes]:
        at = self.codes.index(code)
        return self.shapes[at], self.advances[at], self.bounds[at]


def _read_font3(d: bytes) -> _Font3:
    flags, nl = d[2], d[4]
    p = 5 + nl
    n = struct.unpack_from("<H", d, p)[0]
    table = p + 2
    fmt, size = ("<I", 4) if flags & 0x08 else ("<H", 2)
    offsets = [struct.unpack_from(fmt, d, table + i * size)[0] for i in range(n + 1)]
    shapes = [d[table + offsets[i]:table + offsets[i + 1]] for i in range(n)]
    p = table + offsets[n]
    if not flags & 0x04:
        raise ValueError("DefineFont3 without wide codes")
    codes = list(struct.unpack_from(f"<{n}H", d, p))
    p += 2 * n
    metrics, advances, bounds = b"", [0] * n, [b""] * n
    if flags & 0x80:
        metrics = d[p:p + 6]
        p += 6
        advances = list(struct.unpack_from(f"<{n}h", d, p))
        p += 2 * n
        bounds = []
        for _ in range(n):
            ln = _rect_len(d, p)
            bounds.append(d[p:p + ln])
            p += ln
    return _Font3(d[:5 + nl], flags, codes, shapes, metrics, advances, bounds, d[p:])


def _write_font3(f: _Font3) -> bytes:
    n, flags = len(f.codes), f.flags
    wide = bool(flags & 0x08)
    if not wide and (n + 1) * 2 + sum(map(len, f.shapes)) > 0xFFFF:
        wide = True
        flags |= 0x08
    fmt, size = ("<I", 4) if wide else ("<H", 2)
    pos, table = (n + 1) * size, []
    for s in f.shapes:
        table.append(struct.pack(fmt, pos))
        pos += len(s)
    table.append(struct.pack(fmt, pos))
    layout = b""
    if flags & 0x80:
        layout = f.metrics + struct.pack(f"<{n}h", *f.advances) + b"".join(f.bounds) + f.kerning  # kerning uses codes
    head = f.head[:2] + bytes([flags]) + f.head[3:] + struct.pack("<H", n)
    return head + b"".join(table) + b"".join(f.shapes) + struct.pack(f"<{n}H", *f.codes) + layout


def _add_glyph_font3(d: bytes, code: int) -> bytes | None:
    """DefineFont3 tag body with an empty zero-width glyph for code, None when it already has one."""
    f = _read_font3(d)
    if code in f.codes:
        return None
    f.put(code, EMPTY_SHAPE, 0, EMPTY_RECT)
    return _write_font3(f)


def _alias_glyphs_font3(d: bytes, aliases: dict[int, int]) -> bytes | None:
    """DefineFont3 tag body where each alias code draws its target glyph, None when nothing changes."""
    f = _read_font3(d)
    changed = False
    for code, target in aliases.items():
        if target in f.codes and (code not in f.codes or f.glyph(code) != f.glyph(target)):
            f.put(code, *f.glyph(target))
            changed = True
    return _write_font3(f) if changed else None


def add_empty_glyph(redswf: bytes, code: int) -> bytes:
    """fonts_en.redswf with an empty zero-width glyph for code added to every DefineFont3 missing it."""
    return _edit_fonts(redswf, lambda d: _add_glyph_font3(d, code))


def alias_glyphs(redswf: bytes, aliases: dict[int, int]) -> bytes:
    """fonts_en.redswf where each alias code is drawn with its target glyph in every DefineFont3."""
    return _edit_fonts(redswf, lambda d: _alias_glyphs_font3(d, aliases))


def merge_glyphs(target: bytes, source: bytes) -> bytes:
    """fonts redswf target with every glyph it lacks copied from the source font of the same style.

    Both must use the DefineFont3 EM; the donor is matched on the bold/italic flags, else the regular font.
    """
    donors: dict[int, _Font3] = {}
    for code, d in _tags(_swf_body(source)):
        if code == 75:
            f = _read_font3(d)
            donors.setdefault(f.flags & 0x03, f)
    if not donors:
        raise ValueError("source has no DefineFont3")

    def edit(d: bytes) -> bytes | None:
        f = _read_font3(d)
        src = donors.get(f.flags & 0x03) or donors.get(0) or next(iter(donors.values()))
        have = set(f.codes)
        missing = [i for i, c in enumerate(src.codes) if c not in have]
        for i in missing:
            f.put(src.codes[i], src.shapes[i], src.advances[i], src.bounds[i] or EMPTY_RECT)
        return _write_font3(f) if missing else None

    return _edit_fonts(target, edit)


def _edit_fonts(redswf: bytes, edit) -> bytes:
    at = CR2W_SWF_SIZE + 4
    sig = redswf[at:at + 3]
    if sig not in (b"FWS", b"GFX", b"CWS", b"CFX"):
        raise ValueError("not a fonts redswf")
    stored = struct.unpack_from("<I", redswf, CR2W_SWF_SIZE)[0]
    packed = sig in (b"CWS", b"CFX")
    raw = redswf[at:at + stored]
    swf = raw[:8] + zlib.decompress(raw[8:]) if packed else raw
    nbits = swf[8] >> 3
    p = 8 + (5 + 4 * nbits + 7) // 8 + 4
    out = [swf[8:p]]
    changed = False
    while p + 2 <= len(swf):
        code_len = struct.unpack_from("<H", swf, p)[0]
        tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
        if ln == 0x3F:
            ln = struct.unpack_from("<I", swf, hp)[0]
            hp += 4
        body = swf[hp:hp + ln]
        new = edit(body) if tag == 75 else None
        if new is None:
            out.append(swf[p:hp + ln])
        else:
            out.append(struct.pack("<HI", (tag << 6) | 0x3F, len(new)) + new)
            changed = True
        p = hp + ln
        if tag == 0:
            break
    if not changed:
        return redswf
    body = b"".join(out)
    new_swf = swf[:4] + struct.pack("<I", len(body) + 8) + body
    if packed:
        new_swf = new_swf[:8] + zlib.compress(new_swf[8:], 9)
    delta = len(new_swf) - stored
    head = bytearray(redswf[:at])
    for off in CR2W_FILE_SIZES + (CR2W_EXPORT_SIZE, CR2W_SWF_SIZE):
        struct.pack_into("<I", head, off, struct.unpack_from("<I", head, off)[0] + delta)
    return bytes(head) + new_swf + redswf[at + stored:]
