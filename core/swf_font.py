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
