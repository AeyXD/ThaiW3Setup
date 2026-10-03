import struct, zlib, hashlib
from gamepath import game_path

P = game_path("content", "content0", "bundles", "r4gui.bundle")
f = open(P, "rb")
h = f.read(32)
size, dummy, tsz = struct.unpack_from("<III", h, 8)
print("hdr", h[20:32].hex(), struct.unpack_from("<HI", h, 20))
toc = f.read(tsz)
n = tsz // 304
comps = {}
for i in range(n):
    e = toc[i * 304:(i + 1) * 304]
    name = e[:256].split(b"\0")[0].decode()
    md5 = e[256:272]
    off, usz, zsz, crc, comp = struct.unpack_from("<QIIII", e, 272)
    tail = e[296:304]
    comps[comp] = comps.get(comp, 0) + 1
    if "fonts_en" in name or i < 2:
        f.seek(off)
        z = f.read(zsz)
        raw = zlib.decompress(z) if comp == 1 else z
        print(name, off, usz, zsz, hex(crc), comp, tail.hex())
        print("  md5 entry   ", md5.hex())
        print("  md5 raw     ", hashlib.md5(raw).hexdigest(), "md5 z", hashlib.md5(z).hexdigest())
        print("  crc raw     ", hex(zlib.crc32(raw)), "crc z", hex(zlib.crc32(z)))
        print("  md5 name    ", hashlib.md5(name.encode()).hexdigest(), hashlib.md5(name.lower().encode()).hexdigest())
        print("  raw head", raw[:16], "zhead", z[:4].hex(), "lenraw", len(raw))
print("compression types", comps, "entries", n)
