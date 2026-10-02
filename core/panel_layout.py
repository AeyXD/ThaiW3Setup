"""Readable description text in the journal, glossary, letter and notice board panels.

The description fields are justified, which stretches the gaps at every Thai word break and leaves short
lines with huge gaps, and they have no line spacing, which crowds Thai vowels and tone marks. The panels are
read from the player's own game at install time; justified fields become left-aligned and the large text
bodies get extra leading. The SWF is zlib-compressed inside a CR2W file whose size fields are not all known,
so the recompressed stream is zero-padded to its original length.
"""
from __future__ import annotations

import logging
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from .bundle import BundleFile, iter_bundle
from .logo import GUI_BUNDLE, _fix_crcs, _read_cr2w
from .progress import ProgressFn, noop

log = logging.getLogger(__name__)

# the book and letter popup read from the inventory lives in panel_overlay
PANELS = ("gameplay\\gui_new\\swf\\glossary\\", "gameplay\\gui_new\\swf\\journal\\",
          "gameplay\\gui_new\\swf\\overlay\\panel_overlay.redswf",
          "gameplay\\gui_new\\swf\\noticeboard\\panel_noticeboard.redswf")
DEFINE_EDIT_TEXT = 37
DEFINE_SPRITE = 39
ALIGN_LEFT, ALIGN_JUSTIFY = 0, 3
TWIPS = 20
BODY_MIN_HEIGHT = 400 * TWIPS  # description bodies; titles and short blurbs keep their spacing
BODY_LEADING = 10 * TWIPS


class LayoutError(Exception):
    pass


@dataclass
class _Field:
    align: int  # offset of the layout record: align u8, margins and indent u16, leading s16
    text: int
    text_len: int
    height: int
    multiline: bool


def _rect_len(d: bytes | bytearray, p: int) -> int:
    return (5 + 4 * (d[p] >> 3) + 7) // 8


def _rect_height(d: bytes | bytearray, p: int) -> int:
    nbits = d[p] >> 3
    bits = int.from_bytes(d[p:p + _rect_len(d, p)], "big") >> (_rect_len(d, p) * 8 - 5 - 4 * nbits)
    mask = (1 << nbits) - 1

    def signed(v):
        return v - (1 << nbits) if v >> (nbits - 1) else v
    return signed(bits & mask) - signed((bits >> nbits) & mask)


def _tag_spans(body: bytes | bytearray, p: int, end: int):
    """(code, data start, data length) of every tag, descending into sprites."""
    while p + 2 <= end:
        code_len = struct.unpack_from("<H", body, p)[0]
        p += 2
        code, ln = code_len >> 6, code_len & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, p)[0]
            p += 4
        yield code, p, ln
        if code == DEFINE_SPRITE:
            yield from _tag_spans(body, p + 4, p + ln)
        p += ln
        if code == 0:
            break


def _text_fields(body: bytes | bytearray) -> list[_Field]:
    """Every DefineEditText that has a layout record."""
    found = []
    for code, start, _ln in _tag_spans(body, _rect_len(body, 0) + 4, len(body)):
        if code != DEFINE_EDIT_TEXT:
            continue
        height = _rect_height(body, start + 2)
        p = start + 2 + _rect_len(body, start + 2)
        f1, f2 = body[p], body[p + 1]
        p += 2
        if not f2 & 0x20:
            continue
        if f1 & 0x01:
            p += 2
        if f2 & 0x80:
            p = body.index(b"\0", p) + 1
        if f1 & 0x01 or f2 & 0x80:
            p += 2
        if f1 & 0x04:
            p += 4
        if f1 & 0x02:
            p += 2
        align = p
        p = body.index(b"\0", p + 9) + 1
        text_len = body.index(b"\0", p) - p if f1 & 0x80 else 0
        found.append(_Field(align, p, text_len, height, bool(f1 & 0x20)))
    return found


def _restyle(body: bytearray) -> list[_Field]:
    """Apply the layout changes in place; returns the fields that changed."""
    changed = []
    for f in _text_fields(body):
        before = bytes(body[f.align:f.align + 9])
        if body[f.align] == ALIGN_JUSTIFY:
            body[f.align] = ALIGN_LEFT
        if f.multiline and f.height >= BODY_MIN_HEIGHT:
            leading = struct.unpack_from("<h", body, f.align + 7)[0]
            struct.pack_into("<h", body, f.align + 7, max(leading, BODY_LEADING))
        if body[f.align:f.align + 9] != before:
            changed.append(f)
    return changed


def _deflate(body: bytes) -> bytes:
    def run(level, mem):
        c = zlib.compressobj(level, zlib.DEFLATED, 15, mem)
        return c.compress(body) + c.flush()
    return min((run(level, mem) for level in (6, 9) for mem in (8, 9)), key=len)


def restyle_panel(data: bytes) -> bytes | None:
    """The .redswf with its text fields restyled, or None if nothing changes."""
    cr2w = _read_cr2w(data)
    resource = next((e for e in cr2w.exports if e.cls == "CSwfResource"), None)
    if resource is None:
        raise LayoutError("no CSwfResource")
    at = data.find(b"CFX", resource.props_end, resource.offset + resource.size)
    if at < 0:
        raise LayoutError("no compressed SWF")
    inflater = zlib.decompressobj()
    body = bytearray(inflater.decompress(data[at + 8:resource.offset + resource.size]))
    stream_len = resource.offset + resource.size - at - 8 - len(inflater.unused_data)
    fields = _restyle(body)
    if not fields:
        return None
    stream = _deflate(bytes(body))
    if len(stream) > stream_len:
        # placeholder text, replaced by the game before the field is shown
        for f in fields:
            body[f.text:f.text + f.text_len] = b" " * f.text_len
        stream = _deflate(bytes(body))
    if len(stream) > stream_len:
        raise LayoutError(f"recompressed SWF is {len(stream) - stream_len} bytes larger")
    out = bytearray(data)
    out[at + 8:at + 8 + stream_len] = stream + bytes(stream_len - len(stream))
    _fix_crcs(out, cr2w, {resource.index})
    return bytes(out)


def panel_files(content0: Path, progress: ProgressFn = noop) -> list[BundleFile]:
    """The journal, glossary, letter and notice panels of the game with readable text, ready for a mod bundle."""
    files = []
    for f in iter_bundle(content0 / "bundles" / GUI_BUNDLE,
                         lambda n, _s: n.startswith(PANELS) and n.endswith(".redswf")):
        name = f.path.rsplit("\\", 1)[-1]
        progress(0.0, f"จัดรูปแบบข้อความ {name}...")
        try:
            data = restyle_panel(f.data)
        except (LayoutError, ValueError, struct.error) as exc:
            log.warning("panel %s left as is: %s", name, exc)
            continue
        if data is not None:
            files.append(BundleFile(f.path, data))
    if not files:
        raise LayoutError(f"no text panels restyled in {GUI_BUNDLE}")
    return files
