"""Reader/writer for Witcher 3 .w3strings files (RTSW)."""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field

LANGUAGES = {
    "pl": (0x83496237, 0x73946816),
    "en": (0x43975139, 0x79321793),
    "de": (0x75886138, 0x42791159),
    "it": (0x45931894, 0x12375973),
    "fr": (0x23863176, 0x75921975),
    "cz": (0x24987354, 0x21793217),
    "es": (0x18796651, 0x42387566),
    "zh": (0x18632176, 0x16875467),
    "ru": (0x63481486, 0x42386347),
    "hu": (0x42378932, 0x67823218),
    "jp": (0x54834893, 0x59825646),
    # languages added after release ship unencrypted (key 0)
    "tr": (0, 0),
    "ar": (0, 0),
    "br": (0, 0),
    "kr": (0, 0),
    "esmx": (0, 0),
    "ua": (0, 0),
}


class W3StringsError(Exception):
    pass


def hash_key(key: str) -> int:
    h = 0
    data = key.lower().encode("utf-16-le")
    for i in range(0, len(data), 2):
        h = (h * 31 + (data[i] | (data[i + 1] << 8))) & 0xFFFFFFFF
    return h


def read_bit6(f: io.BufferedIOBase) -> int:
    result = 0
    shift = 0
    i = 1
    while True:
        raw = f.read(1)
        if not raw:
            raise W3StringsError("unexpected end of file in bit6 value")
        b = raw[0]
        s = 6
        mask = 0xFF
        if b > 127:
            mask = 127
            s = 7
        elif b > 63 and i == 1:
            mask = 63
        if shift < 32:
            result |= (b & mask) << shift
        shift += s
        if b < 64 or (i >= 3 and b < 128):
            break
        i += 1
    return result


def write_bit6(out: bytearray, c: int) -> None:
    if c == 0:
        out.append(128)
        return
    parts = []
    left = c
    i = 0
    while left > 0:
        if i == 0:
            parts.append(left & 63)
            left >>= 6
        else:
            parts.append(left & 255)
            left >>= 7
        i += 1
    n = len(parts)
    for i, val in enumerate(parts):
        last = i == n - 1
        cleft = (n - 1) - i
        if not last:
            if cleft >= 1 and i >= 1:
                val |= 128
            elif val < 64:
                val |= 64
            else:
                val |= 128
        out.append(val & 0xFF)


VERSION_UTF16 = 162
VERSION_UTF8 = 164


def _xor_utf16(raw: bytes, strlen: int, key_init: int) -> bytes:
    out = bytearray(len(raw))
    key = key_init
    mult = strlen + 1
    for i in range(0, len(raw), 2):
        ck = (mult * key) & 0xFFFF
        out[i] = raw[i] ^ (ck & 0xFF)
        out[i + 1] = raw[i + 1] ^ (ck >> 8)
        key = ((key << 1) | (key >> 15)) & 0xFFFF
    return bytes(out)


def _xor_utf8(raw: bytes, strlen: int, key_init: int) -> bytes:
    out = bytearray(len(raw))
    key = key_init
    mult = strlen + 1
    for i in range(len(raw)):
        out[i] = raw[i] ^ ((mult * key) & 0xFF)
        key = ((key << 1) | (key >> 15)) & 0xFFFF
    return bytes(out)


@dataclass
class W3Strings:
    language: str = "en"
    version: int = 162
    # str_id -> text
    strings: dict[int, str] = field(default_factory=dict)
    # str_id -> key hash
    keys: dict[int, int] = field(default_factory=dict)
    # bytes found after the string buffer (newer game builds); preserved as-is
    trailer: bytes = b""

    @classmethod
    def load(cls, path, language: str | None = None) -> "W3Strings":
        with open(path, "rb") as fh:
            return cls.parse(fh.read(), language)

    @classmethod
    def parse(cls, data: bytes, language: str | None = None) -> "W3Strings":
        """Parse a file. ``language`` disambiguates files sharing key 0 (tr, ar, ...)."""
        if data[:4] != b"RTSW":
            raise W3StringsError("not a w3strings file")
        version, key1 = struct.unpack_from("<IH", data, 4)
        key2 = struct.unpack_from("<H", data, len(data) - 2)[0]
        full_key = (key1 << 16) | key2
        if language:
            expected = LANGUAGES.get(language, (None,))[0]
            # third-party tools rewrite the file with a foreign footer; the header half identifies it
            ok = expected == full_key or (expected is not None and key1 == expected >> 16)
            lang = language if ok else None
        else:
            lang = next((h for h, (k, _) in LANGUAGES.items() if k == full_key), None)
        if lang is None:
            raise W3StringsError(f"unknown language key {full_key:08x}")
        magic = LANGUAGES[lang][1]

        f = io.BytesIO(data)
        f.seek(10)
        n1 = read_bit6(f)
        block1 = []
        for _ in range(n1):
            sid, off, slen = struct.unpack("<III", f.read(12))
            block1.append((sid ^ magic, off, slen))
        if block1 and sum(sid >= 1 << 25 for sid, _o, _l in block1) * 2 > len(block1):
            raise W3StringsError(f"string ids do not decode as {lang}")
        n2 = read_bit6(f)
        keys = {}
        for _ in range(n2):
            khex, sid = struct.unpack("<II", f.read(8))
            keys[sid ^ magic] = khex
        n3 = read_bit6(f)
        start = f.tell()
        utf8 = version >= VERSION_UTF8
        unit = 1 if utf8 else 2
        end = start + n3 * unit
        if end > len(data) - 2:
            raise W3StringsError(f"string buffer overruns file (version {version})")
        trailer = data[end:len(data) - 2]

        key_init = (magic >> 8) & 0xFFFF
        strings = {}
        for sid, off, slen in block1:
            pos = start + off * unit
            raw = data[pos:pos + slen * unit]
            if utf8:
                strings[sid] = _xor_utf8(raw, slen, key_init).decode("utf-8", "replace")
            else:
                strings[sid] = _xor_utf16(raw, slen, key_init).decode("utf-16-le", "surrogatepass")
        return cls(language=lang, version=version, strings=strings, keys=keys, trailer=trailer)

    def build(self) -> bytes:
        key, magic = LANGUAGES[self.language]
        key_init = (magic >> 8) & 0xFFFF
        ids = sorted(self.strings, key=lambda s: s ^ magic)

        utf8 = self.version >= VERSION_UTF8
        unit = 1 if utf8 else 2
        buf = bytearray()
        entries = []
        for sid in ids:
            if utf8:
                text = self.strings[sid].encode("utf-8")
                slen = len(text)
                entries.append((sid ^ magic, len(buf), slen))
                buf += _xor_utf8(text, slen, key_init)
                buf += b"\x00"
            else:
                text = self.strings[sid].encode("utf-16-le", "surrogatepass")
                slen = len(text) // 2
                entries.append((sid ^ magic, len(buf) // 2, slen))
                buf += _xor_utf16(text, slen, key_init)
                buf += b"\x00\x00"

        out = bytearray(b"RTSW")
        out += struct.pack("<IH", self.version, key >> 16)
        write_bit6(out, len(entries))
        for e in entries:
            out += struct.pack("<III", *e)
        key_items = sorted((k, sid) for sid, k in self.keys.items())
        write_bit6(out, len(key_items))
        for khex, sid in key_items:
            out += struct.pack("<II", khex, sid ^ magic)
        write_bit6(out, len(buf) // unit)
        out += buf
        out += self.trailer
        out += struct.pack("<H", key & 0xFFFF)
        return bytes(out)

    def save(self, path) -> None:
        with open(path, "wb") as fh:
            fh.write(self.build())
