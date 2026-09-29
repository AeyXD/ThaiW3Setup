"""Writer for metadata.store (version 7, as shipped with the Remastered edition).

Layout (all arrays are VLQ-count prefixed and start with an all-zero element):
  header      magic '\\x03VTM', version, max size in bundle, max size in memory
  strtab      VLQ size + NUL separated names
  fileInfo    name, pathHash, sizeInBundle, sizeInMemory, firstEntry, bufferId, bufferCount, compression
  fileEntry   offset(u64), sizeInBundle, nextEntry, fileId, bundleId
  bundleInfo  dataSize(u64), dataOffset, name, firstEntry, numEntries
  buffers     u32 list
  dirInit     name, parent
  fileInit    fileId, dirId, name
  hashes      fnv1a64(lowercase path), fileId (sorted by hash)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .bundle import PackedEntry, COMP_ZLIB

VERSION = 7


def fnv1a64(text: str) -> int:
    h = 0xCBF29CE484222325
    for c in text.lower().encode("latin-1"):
        h ^= c
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def _vlq(value: int) -> bytes:
    out = bytearray()
    b = value & 0x3F
    value >>= 6
    if value:
        b |= 0x40
    out.append(b)
    while value:
        b = value & 0x7F
        value >>= 7
        if value:
            b |= 0x80
        out.append(b)
    return bytes(out)


class _StrTab:
    def __init__(self):
        self.data = bytearray(b"\0")

    def add(self, s: str) -> int:
        off = len(self.data)
        self.data += s.encode("latin-1") + b"\0"
        return off


@dataclass
class BundleLayout:
    name: str
    size: int
    data_offset: int
    entries: list[PackedEntry]


def build_metastore(bundle: BundleLayout) -> bytes:
    st = _StrTab()
    bundle_name = st.add(bundle.name)
    file_names = [st.add(e.path) for e in bundle.entries]

    dirs: list[tuple[int, int]] = [(st.add(""), 0)]
    dir_index: dict[str, int] = {"": 0}
    file_init = []
    for fid, e in enumerate(bundle.entries, start=1):
        parts = e.path.split("\\")
        parent = 0
        key = ""
        for part in parts[:-1]:
            key = f"{key}\\{part}" if key else part
            if key not in dir_index:
                dir_index[key] = len(dirs)
                dirs.append((st.add(part), parent))
            parent = dir_index[key]
        file_init.append((fid, parent, st.add(parts[-1])))

    file_info = [(0,) * 8]
    file_entry = [(0, 0, 0, 0, 0)]
    for fid, (e, name) in enumerate(zip(bundle.entries, file_names), start=1):
        comp = 1 if e.compression == COMP_ZLIB else 0
        file_info.append((name, 0, e.zsize, e.size, fid, 0, 0, comp))
        file_entry.append((e.offset, e.zsize, 0, fid, 1))
    bundle_info = [(0, 0, 0, 0, 0),
                   (bundle.size - bundle.data_offset, bundle.data_offset, bundle_name, 1, len(bundle.entries))]
    hashes = sorted((fnv1a64(e.path), fid) for fid, e in enumerate(bundle.entries, start=1))

    out = bytearray(b"\x03VTM")
    out += struct.pack("<III", VERSION,
                       max((e.zsize for e in bundle.entries), default=0),
                       max((e.size for e in bundle.entries), default=0))
    out += _vlq(len(st.data)) + st.data

    def table(fmt, rows):
        nonlocal out
        out += _vlq(len(rows))
        for row in rows:
            out += struct.pack(fmt, *row)

    table("<8I", file_info)
    table("<QIIII", file_entry)
    table("<QIIII", bundle_info)
    out += _vlq(0)  # buffers
    table("<2i", dirs)
    table("<3i", file_init)
    table("<QQ", hashes)
    return bytes(out)
