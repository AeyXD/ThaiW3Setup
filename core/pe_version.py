"""Read an exe's VERSIONINFO without Windows. Only what identify() needs: the four file-version numbers.

Layout per the PE/COFF spec: DOS stub -> PE header -> section table -> the .rsrc section holds a tree of
resource directories (type -> name -> language) whose leaves point at the data by RVA.
"""
from __future__ import annotations

import logging
import os
import struct
from pathlib import Path

log = logging.getLogger(__name__)

RT_VERSION = 16
FIXEDFILEINFO_SIGNATURE = 0xFEEF04BD
DIRECTORY_ENTRY_RESOURCE = 2
# the DOS stub, PE header and section table all live well inside this
HEADER_BYTES = 8192
# a resource directory entry's high bit marks a subdirectory rather than a leaf
SUBDIRECTORY = 0x80000000


class _Rsrc:
    """The .rsrc section, addressed the way the resource tree expects (offsets relative to the section)."""

    def __init__(self, data: bytes, base_rva: int):
        self.data = data
        self.base_rva = base_rva

    def first_entry(self, offset: int) -> int | None:
        """Offset of the first child of the directory at `offset`, named or not."""
        if offset + 24 > len(self.data):
            return None
        named, unnamed = struct.unpack_from("<HH", self.data, offset + 12)
        if named + unnamed == 0:
            return None
        return struct.unpack_from("<I", self.data, offset + 16 + 4)[0]

    def find_entry(self, offset: int, wanted_id: int) -> int | None:
        """Offset of the child with this integer id, or None."""
        if offset + 16 > len(self.data):
            return None
        named, unnamed = struct.unpack_from("<HH", self.data, offset + 12)
        start = offset + 16 + named * 8  # id entries follow the named ones
        for i in range(unnamed):
            pos = start + i * 8
            if pos + 8 > len(self.data):
                return None
            entry_id, value = struct.unpack_from("<II", self.data, pos)
            if entry_id == wanted_id:
                return value
        return None


def _sections(data: bytes) -> tuple[list[tuple[int, int, int]], int] | None:
    """[(virtual_address, raw_size, raw_offset)] plus the resource directory's RVA."""
    if len(data) < 0x40 or data[:2] != b"MZ":
        return None
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if pe + 24 > len(data) or data[pe:pe + 4] != b"PE\0\0":
        return None
    n_sections, = struct.unpack_from("<H", data, pe + 6)
    opt_size, = struct.unpack_from("<H", data, pe + 20)
    opt = pe + 24
    if opt + 2 > len(data):
        return None
    magic, = struct.unpack_from("<H", data, opt)
    if magic == 0x20B:  # PE32+
        dirs, n_dirs_at = opt + 112, opt + 108
    elif magic == 0x10B:  # PE32
        dirs, n_dirs_at = opt + 96, opt + 92
    else:
        return None
    n_dirs, = struct.unpack_from("<I", data, n_dirs_at)
    if n_dirs <= DIRECTORY_ENTRY_RESOURCE:
        return None
    rsrc_rva, = struct.unpack_from("<I", data, dirs + DIRECTORY_ENTRY_RESOURCE * 8)
    table = opt + opt_size
    out = []
    for i in range(n_sections):
        pos = table + i * 40
        if pos + 40 > len(data):
            break
        va, raw_size, raw_off = struct.unpack_from("<III", data, pos + 12)
        out.append((va, raw_size, raw_off))
    return out, rsrc_rva


def _version_resource(rsrc: _Rsrc) -> bytes | None:
    type_dir = rsrc.find_entry(0, RT_VERSION)
    if type_dir is None or not type_dir & SUBDIRECTORY:
        return None
    name_dir = rsrc.first_entry(type_dir & ~SUBDIRECTORY)
    if name_dir is None or not name_dir & SUBDIRECTORY:
        return None
    leaf = rsrc.first_entry(name_dir & ~SUBDIRECTORY)
    if leaf is None or leaf & SUBDIRECTORY or leaf + 8 > len(rsrc.data):
        return None
    data_rva, data_size = struct.unpack_from("<II", rsrc.data, leaf)
    start = data_rva - rsrc.base_rva
    if start < 0 or start + data_size > len(rsrc.data):
        return None
    return rsrc.data[start:start + data_size]


def file_version(path: Path | str) -> str:
    """File version of a PE as "a.b.c.d", or "" when the file has none or cannot be read."""
    try:
        with open(path, "rb") as f:
            parsed = _sections(f.read(HEADER_BYTES))
            if not parsed:
                return ""
            sections, rsrc_rva = parsed
            section = next((s for s in sections if s[0] <= rsrc_rva < s[0] + s[1]), None)
            if section is None or not rsrc_rva:
                return ""
            va, size, off = section
            f.seek(0, os.SEEK_END)
            end = f.tell()
            if off >= end:
                return ""
            f.seek(off)
            rsrc = _Rsrc(f.read(min(size, end - off)), va)  # only the resources, not the whole exe
        resource = _version_resource(rsrc)
    except OSError as exc:
        log.warning("cannot read %s: %s", path, exc)
        return ""
    except struct.error as exc:  # a truncated or hand-mangled file reads past its own end
        log.warning("malformed PE %s: %s", path, exc)
        return ""
    if not resource:
        return ""
    # VS_VERSIONINFO: header, the key "VS_VERSION_INFO", padding, then VS_FIXEDFILEINFO
    at = resource.find(struct.pack("<I", FIXEDFILEINFO_SIGNATURE))
    if at < 0 or at + 20 > len(resource):
        return ""
    ms, ls = struct.unpack_from("<II", resource, at + 8)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
