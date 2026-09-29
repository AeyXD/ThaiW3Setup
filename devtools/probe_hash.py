import struct, sys, zlib, hashlib

sys.path.insert(0, r"C:\Users\saetanpee\AppData\Local\Temp\w3thai_baseline")

MOD = r"C:\Users\saetanpee\Downloads\w3tu\Tools\modFontCsPraKas\content\metadata.store"
PATH = "gameplay\\gui_new\\swf\\witcher3\\fonts_en.redswf"
TARGET = 0xC07E0D30533B9EBF


def fnv1a64(b, basis=0xCBF29CE484222325):
    h = basis
    for c in b:
        h ^= c
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def fnv1_64(b, basis=0xCBF29CE484222325):
    h = basis
    for c in b:
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        h ^= c
    return h


cands = {
    "raw": PATH.encode(),
    "lower": PATH.lower().encode(),
    "slash": PATH.replace("\\", "/").encode(),
    "utf16": PATH.encode("utf-16-le"),
    "utf16lower": PATH.lower().encode("utf-16-le"),
}
for n, b in cands.items():
    for fn in (fnv1a64, fnv1_64):
        for suffix in (b"", b"\0"):
            h = fn(b + suffix)
            flag = " <== MATCH" if h == TARGET else ""
            print(f"{n:10} {fn.__name__:8} {suffix!r:6} {h:016x}{flag}")
print("target", hex(TARGET))
