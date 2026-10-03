"""core/pe_version.py reads VERSIONINFO out of a PE the way the Windows API does."""
import os, struct, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from core.pe_version import file_version

RSRC_VA = 0x4000
RSRC_RAW = 0x400


def version_resource(ms: int, ls: int) -> bytes:
    """A VS_VERSIONINFO carrying just VS_FIXEDFILEINFO: wLength, wValueLength, wType, key, padding, value."""
    key = "VS_VERSION_INFO\0".encode("utf-16-le")
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x10000, ms, ls, ms, ls, 0x3F, 0, 0x40004, 1, 0, 0, 0)
    head = struct.pack("<HHH", 0, len(fixed), 0) + key
    head += b"\0" * (-len(head) % 4)
    body = head + fixed
    return struct.pack("<H", len(body)) + body[2:]  # wLength counts the whole structure


def directory(entries: list[tuple[int, int]]) -> bytes:
    """One IMAGE_RESOURCE_DIRECTORY with id entries only."""
    out = struct.pack("<IIHHHH", 0, 0, 0, 0, 0, len(entries))
    for entry_id, value in entries:
        out += struct.pack("<II", entry_id, value)
    return out


def rsrc_section(payload: bytes, res_type: int = 16) -> bytes:
    """type dir -> name dir -> language dir -> data entry -> payload, laid out back to back."""
    one = len(directory([(0, 0)]))            # a directory holding a single entry
    type_off, name_off, lang_off = 0, one, one * 2
    leaf_off = one * 3
    data_off = leaf_off + 16
    blob = directory([(res_type, name_off | 0x80000000)])
    blob += directory([(1, lang_off | 0x80000000)])
    blob += directory([(0x409, leaf_off)])
    blob += struct.pack("<IIII", RSRC_VA + data_off, len(payload), 0, 0)
    blob += payload
    return blob


def pe(sections: list[tuple[bytes, int, bytes]], rsrc_rva: int, plus: bool = True) -> bytes:
    """A PE whose headers are real enough to walk; no code, no imports."""
    opt = struct.pack("<H", 0x20B if plus else 0x10B) + b"\0" * ((108 if plus else 92) - 2)
    opt += struct.pack("<I", 16)                      # NumberOfRvaAndSizes
    opt += struct.pack("<II", 0, 0)                   # export
    opt += struct.pack("<II", 0, 0)                   # import
    opt += struct.pack("<II", rsrc_rva, 0)            # resource
    opt += b"\0" * (13 * 8)
    coff = struct.pack("<HHIIIHH", 0x8664, len(sections), 0, 0, 0, len(opt), 0x22)
    headers = b"PE\0\0" + coff + opt
    table = b""
    for name, va, data in sections:
        table += name.ljust(8, b"\0") + struct.pack("<IIII", len(data), va, len(data), RSRC_RAW) + b"\0" * 16
    stub = b"MZ" + b"\0" * 0x3A + struct.pack("<I", 0x40)
    out = bytearray(stub + headers + table)
    out += b"\0" * (RSRC_RAW - len(out))
    for _, _, data in sections:
        out += data
    return bytes(out)


def write(data: bytes) -> str:
    path = Path(tempfile.mkdtemp()) / "witcher3.exe"
    path.write_bytes(data)
    return str(path)


blob = rsrc_section(version_resource(5 << 16 | 0, 15 << 16 | 61352))
got = file_version(write(pe([(b".rsrc", RSRC_VA, blob)], RSRC_VA)))
assert got == "5.0.15.61352", got

blob = rsrc_section(version_resource(4 << 16 | 4, 0))
assert file_version(write(pe([(b".rsrc", RSRC_VA, blob)], RSRC_VA, plus=False))) == "4.4.0.0", "PE32 too"

# a resource section with no RT_VERSION in it
blob = rsrc_section(version_resource(1 << 16, 0), res_type=3)  # RT_ICON
assert file_version(write(pe([(b".rsrc", RSRC_VA, blob)], RSRC_VA))) == ""

# nothing to read: no resource directory, not a PE at all, truncated, missing
assert file_version(write(pe([(b".text", RSRC_VA, b"\0" * 64)], 0))) == ""
assert file_version(write(b"#!/bin/sh\necho hello\n")) == ""
assert file_version(write(pe([(b".rsrc", RSRC_VA, blob)], RSRC_VA)[:200])) == ""
assert file_version("/nonexistent/witcher3.exe") == ""

print("test_pe_version ok")
