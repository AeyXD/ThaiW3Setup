"""Reader/writer for Witcher 3 POTATO70 bundles.

Two TOC layouts exist:
  * v3 (1.3x / 4.0x): 320-byte entries, 32-bit offsets, data aligned to 4 KiB,
    usually LZ4 compressed.
  * v5 (Remastered): 304-byte entries, 64-bit offsets, data packed right after
    the TOC, zlib compressed.
The writer always produces v5 so the files match what the Remastered engine ships.
"""
from __future__ import annotations

import struct
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass

MAGIC = b"POTATO70"
HEADER_SIZE = 32
V3_ENTRY = 320
V5_ENTRY = 304

COMP_NONE = 0
COMP_ZLIB = 1
COMP_LZ4 = (4, 5)


class BundleError(Exception):
    pass


def lz4_block_decompress(src: bytes, size: int) -> bytes:
    dst = bytearray()
    i = 0
    n = len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        dst += src[i:i + lit]
        i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        mlen = token & 15
        if mlen == 15:
            while True:
                b = src[i]
                i += 1
                mlen += b
                if b != 255:
                    break
        mlen += 4
        start = len(dst) - off
        if start < 0:
            raise BundleError("corrupt LZ4 stream")
        if off >= mlen:
            dst += dst[start:start + mlen]
        else:
            for k in range(mlen):
                dst.append(dst[start + k])
    if len(dst) != size:
        raise BundleError(f"LZ4 size mismatch: {len(dst)} != {size}")
    return bytes(dst)


@dataclass
class BundleFile:
    path: str
    data: bytes


def read_bundle(path) -> list[BundleFile]:
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:8] != MAGIC:
        raise BundleError(f"{path}: not a POTATO70 bundle")
    _, _, toc_size = struct.unpack_from("<III", blob, 8)
    version = struct.unpack_from("<H", blob, 20)[0]
    toc = blob[HEADER_SIZE:HEADER_SIZE + toc_size]
    files = []
    if version >= 5:
        for i in range(toc_size // V5_ENTRY):
            e = toc[i * V5_ENTRY:(i + 1) * V5_ENTRY]
            name = e[:256].split(b"\0")[0].decode("latin-1")
            off, usz, zsz, _crc, comp = struct.unpack_from("<QIIII", e, 272)
            files.append(BundleFile(name, _unpack(blob[off:off + zsz], usz, comp)))
    else:
        for i in range(toc_size // V3_ENTRY):
            e = toc[i * V3_ENTRY:(i + 1) * V3_ENTRY]
            name = e[:256].split(b"\0")[0].decode("latin-1")
            usz, zsz, off = struct.unpack_from("<III", e, 276)
            comp = struct.unpack_from("<I", e, 316)[0]
            files.append(BundleFile(name, _unpack(blob[off:off + zsz], usz, comp)))
    return files


def iter_bundle(path, want: Callable[[str, int], bool]) -> Iterator[BundleFile]:
    """Files of a bundle for which ``want(path, size)`` is true, read one at a time."""
    with open(path, "rb") as fh:
        head = fh.read(HEADER_SIZE)
        if head[:8] != MAGIC:
            raise BundleError(f"{path}: not a POTATO70 bundle")
        toc_size = struct.unpack_from("<I", head, 16)[0]
        version = struct.unpack_from("<H", head, 20)[0]
        toc = fh.read(toc_size)
        entry = V5_ENTRY if version >= 5 else V3_ENTRY
        for i in range(toc_size // entry):
            e = toc[i * entry:(i + 1) * entry]
            name = e[:256].split(b"\0")[0].decode("latin-1")
            if version >= 5:
                off, usz, zsz, _crc, comp = struct.unpack_from("<QIIII", e, 272)
            else:
                usz, zsz, off = struct.unpack_from("<III", e, 276)
                comp = struct.unpack_from("<I", e, 316)[0]
            if not want(name, usz):
                continue
            fh.seek(off)
            yield BundleFile(name, _unpack(fh.read(zsz), usz, comp))


def _unpack(z: bytes, size: int, comp: int) -> bytes:
    if comp == COMP_NONE:
        return z[:size]
    if comp == COMP_ZLIB:
        return zlib.decompress(z)
    if comp in COMP_LZ4:
        return lz4_block_decompress(z, size)
    raise BundleError(f"unsupported compression type {comp}")


@dataclass
class PackedEntry:
    path: str
    offset: int
    size: int
    zsize: int
    compression: int


def write_bundle(path, files: list[BundleFile]) -> tuple[int, int, list[PackedEntry]]:
    """Write a v5 bundle. Returns (file size, data offset, entries)."""
    toc_size = V5_ENTRY * len(files)
    data_offset = HEADER_SIZE + toc_size
    toc = bytearray()
    body = bytearray()
    entries = []
    for bf in files:
        z = zlib.compress(bf.data, 9)
        if len(z) < len(bf.data):
            payload, comp = z, COMP_ZLIB
        else:
            payload, comp = bf.data, COMP_NONE
        off = data_offset + len(body)
        name = bf.path.encode("latin-1")
        if len(name) >= 256:
            raise BundleError(f"path too long: {bf.path}")
        toc += name.ljust(256, b"\0")
        toc += b"\0" * 16
        toc += struct.pack("<QIIII", off, len(bf.data), len(payload), zlib.crc32(bf.data), comp)
        toc += b"\0" * 8
        body += payload
        entries.append(PackedEntry(bf.path, off, len(bf.data), len(payload), comp))
    total = data_offset + len(body)
    header = MAGIC + struct.pack("<IIIHI", total, 0, toc_size, 5, data_offset) + b"\0" * 6
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(toc)
        fh.write(body)
    return total, data_offset, entries
