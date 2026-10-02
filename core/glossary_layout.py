"""Left-aligned description text in the glossary panels (bestiary, encyclopedia, storybook...).

Their description fields are justified, which stretches the gaps at every Thai word break and leaves short
lines with huge gaps. The panels are read from the player's own game at install time and the align byte of
each justified DefineEditText is set to left. The SWF is zlib-compressed inside a CR2W file whose size fields
are not all known, so the recompressed stream is zero-padded to its original length.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

from .bundle import BundleFile, iter_bundle
from .logo import GUI_BUNDLE, _fix_crcs, _read_cr2w
from .progress import ProgressFn, noop

GLOSSARY_DIR = "gameplay\\gui_new\\swf\\glossary\\"
DEFINE_EDIT_TEXT = 37
DEFINE_SPRITE = 39
ALIGN_LEFT, ALIGN_JUSTIFY = 0, 3


class LayoutError(Exception):
    pass


def _rect_len(d: bytes | bytearray, p: int) -> int:
    return (5 + 4 * (d[p] >> 3) + 7) // 8


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


def _justified_fields(body: bytes | bytearray) -> list[tuple[int, int, int]]:
    """(align offset, initial text offset, initial text length) of every justified DefineEditText."""
    found = []
    for code, start, ln in _tag_spans(body, _rect_len(body, 0) + 4, len(body)):
        if code != DEFINE_EDIT_TEXT:
            continue
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
        if body[p] != ALIGN_JUSTIFY:
            continue
        align = p
        p = body.index(b"\0", p + 9) + 1
        text_len = body.index(b"\0", p) - p if f1 & 0x80 else 0
        found.append((align, p, text_len))
    return found


def _deflate(body: bytes) -> bytes:
    def run(level, mem):
        c = zlib.compressobj(level, zlib.DEFLATED, 15, mem)
        return c.compress(body) + c.flush()
    return min((run(level, mem) for level in (6, 9) for mem in (8, 9)), key=len)


def left_align(data: bytes) -> bytes | None:
    """The .redswf with its justified text fields left-aligned, or None if it has none."""
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
    fields = _justified_fields(body)
    if not fields:
        return None
    for align, _text, _ln in fields:
        body[align] = ALIGN_LEFT
    stream = _deflate(bytes(body))
    if len(stream) > stream_len:
        for _align, text, ln in fields:
            body[text:text + ln] = b" " * ln
        stream = _deflate(bytes(body))
    if len(stream) > stream_len:
        raise LayoutError(f"recompressed SWF is {len(stream) - stream_len} bytes larger")
    out = bytearray(data)
    out[at + 8:at + 8 + stream_len] = stream + bytes(stream_len - len(stream))
    _fix_crcs(out, cr2w, {resource.index})
    return bytes(out)


def glossary_files(content0: Path, progress: ProgressFn = noop) -> list[BundleFile]:
    """The glossary panels of the game with left-aligned descriptions, ready for a mod bundle."""
    files = []
    for f in iter_bundle(content0 / "bundles" / GUI_BUNDLE,
                         lambda n, _s: n.startswith(GLOSSARY_DIR) and n.endswith(".redswf")):
        progress(0.0, f"จัดข้อความชิดซ้าย {f.path.rsplit(chr(92), 1)[-1]}...")
        data = left_align(f.data)
        if data is not None:
            files.append(BundleFile(f.path, data))
    if not files:
        raise LayoutError(f"no justified glossary panels in {GUI_BUNDLE}")
    return files
