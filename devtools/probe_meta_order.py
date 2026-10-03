import struct, sys
sys.path.insert(0, r"C:\Users\saetanpee\AppData\Local\Temp\w3thai_baseline")
from gamepath import game_path
from probe_meta import R

B = game_path("content", "content0", "bundles", "blob.bundle")
with open(B, "rb") as fh:
    h = fh.read(32)
    print("blob header", struct.unpack_from("<IIIHI", h, 8), "toc entries", struct.unpack_from("<I", h, 16)[0] / 304)

d = open(game_path("content", "metadata.store"), "rb").read()
r = R(d); r.take(4); r.u32(); r.u32(); r.u32()
st = r.vlq(); strtab = d[r.p:r.p + st]; r.p += st

def s(o):
    return strtab[o:strtab.index(b"\0", o)].decode("latin-1")

def rd(fmt, w):
    n = r.vlq(); v = [struct.unpack_from(fmt, d, r.p + i * w) for i in range(n)]; r.p += n * w; return v

fi = rd("<8I", 32); fe = rd("<QIIII", 24); bi = rd("<QIIII", 24); buf = rd("<I", 4)
di = rd("<2i", 8); fin = rd("<3i", 12); hs = rd("<QQ", 16)
print("dir sample", [(s(a), b) for a, b in di[:8]])
print("parents before children", all(p < i or i == 0 for i, (_, p) in enumerate(di)))
print("fileInit sample", [(a, b, s(c)) for a, b, c in fin[:4]])
print("hash sorted", all(hs[i][0] <= hs[i + 1][0] for i in range(len(hs) - 1)))
print("hash sample", [(hex(a), b, s(fi[b][0])) for a, b in hs[:3]])
print("strtab[0:1]", strtab[:1], "dir0 name offset", di[0])
print("fileInit sorted by file", all(fin[i][0] < fin[i + 1][0] for i in range(len(fin) - 1)))
print("fi.first == index", sum(1 for i, f in enumerate(fi) if f[4] == i), "of", len(fi))
blob_first = [e for e in fe if e[4] == 1][:2]
print("blob first entries", blob_first)
