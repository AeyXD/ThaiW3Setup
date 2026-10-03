import re, sys, os, zlib, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import game_path
from core.bundle import read_bundle

GAME = game_path("content", "content0", "bundles", "r4gui.bundle")
MOD = r"C:\Users\saetanpee\Downloads\w3tu\Tools\modFontCsPraKas\content\blob0.bundle"


def swf_of(data):
    for sig in (b"CWS", b"FWS", b"GFX", b"CFX"):
        i = data.find(sig)
        while i >= 0:
            ver = data[i + 3]
            ln = struct.unpack_from("<I", data, i + 4)[0]
            if 5 <= ver <= 40 and 100 < ln < 50_000_000:
                body = data[i + 8:]
                if sig in (b"CWS", b"CFX"):
                    try:
                        body = zlib.decompressobj().decompress(body)
                    except zlib.error:
                        i = data.find(sig, i + 1)
                        continue
                return sig, ver, ln, body
            i = data.find(sig, i + 1)
    return None


def tags(body):
    nbits = body[0] >> 3
    rect = (5 + 4 * nbits + 7) // 8
    p = rect + 4
    out = []
    while p + 2 <= len(body):
        code_len = struct.unpack_from("<H", body, p)[0]
        p += 2
        code, ln = code_len >> 6, code_len & 0x3F
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, p)[0]
            p += 4
        out.append((code, body[p:p + ln]))
        p += ln
        if code == 0:
            break
    return out


def fonts(body):
    res = []
    for code, d in tags(body):
        if code in (48, 75):  # DefineFont2/3
            fid, flags, lang, nl = struct.unpack_from("<HBBB", d, 0)
            name = d[5:5 + nl].split(b"\0")[0].decode("latin-1")
            nglyph = struct.unpack_from("<H", d, 5 + nl)[0]
            res.append(("DefineFont%d" % (2 if code == 48 else 3), fid, name, nglyph))
        elif code == 56:  # ExportAssets
            n = struct.unpack_from("<H", d, 0)[0]
            p = 2
            for _ in range(n):
                cid = struct.unpack_from("<H", d, p)[0]
                p += 2
                e = d.index(b"\0", p)
                res.append(("Export", cid, d[p:e].decode("latin-1")))
                p = e + 1
        elif code == 88:  # DefineFontName
            fid = struct.unpack_from("<H", d, 0)[0]
            res.append(("FontName", fid, d[2:].split(b"\0")[0].decode("latin-1")))
    return res


for label, path in (("GAME", GAME), ("MOD", MOD)):
    files = {f.path: f.data for f in read_bundle(path)}
    data = files["gameplay\\gui_new\\swf\\witcher3\\fonts_en.redswf"]
    s = swf_of(data)
    if not s:
        print(label, "no swf found")
        continue
    print(label, s[0], "ver", s[1], "len", s[2])
    for r in fonts(s[3]):
        print("   ", r)
