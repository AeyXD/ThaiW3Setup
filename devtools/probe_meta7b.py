import sys, struct
sys.path.insert(0, r"C:\Users\saetanpee\AppData\Local\Temp\w3thai_baseline")
from gamepath import game_path
from probe_meta import R

d = open(game_path("content", "metadata.store"), "rb").read()
r = R(d); r.take(4); r.u32(); r.u32(); r.u32()
st = r.vlq(); strtab = d[r.p:r.p + st]; r.p += st

def s(o):
    return strtab[o:strtab.index(b"\0", o)].decode("latin-1")

nf = r.vlq(); fi = [struct.unpack_from("<8I", d, r.p + i * 32) for i in range(nf)]; r.p += nf * 32
ne = r.vlq(); fe = [struct.unpack_from("<QIIII", d, r.p + i * 24) for i in range(ne)]; r.p += ne * 24
nb = r.vlq(); bi = [struct.unpack_from("<QIIII", d, r.p + i * 24) for i in range(nb)]; r.p += nb * 24
print("files", nf, "entries", ne, "bundles", nb)
for b in bi[:4]:
    print("  bundle", b, s(b[2]) if b[2] else "")
ok = sum(1 for i in range(1, nf) if fe[fi[i][4]][3] == i)
print("fileInfo.first -> entry.fileID match:", ok, "of", nf - 1)
print("fi[1]", fi[1], s(fi[1][0]), "fe[first]", fe[fi[1][4]])
print("fe[1]", fe[1], "fi[fe1.fileID]", fi[fe[1][3]], s(fi[fe[1][3]][0]))
comp = {}
for f in fi[1:]:
    comp[f[5]] = comp.get(f[5], 0) + 1
print("compression types", comp)
print("fields 6,7 nonzero", sum(1 for f in fi if f[6] or f[7]))
nxt = sum(1 for e in fe if e[2])
print("entries with next", nxt)
# rest
print("after bundles at", r.p)
nbuf = r.vlq(); print("buffers", nbuf); r.p += nbuf * 4
nd = r.vlq(); print("dirInit", nd, d[r.p:r.p + 24].hex(" ")); r.p += nd * 8
nfi = r.vlq(); print("fileInit", nfi, d[r.p:r.p + 24].hex(" ")); r.p += nfi * 12
nh = r.vlq(); print("hashes", nh, d[r.p:r.p + 32].hex(" ")); r.p += nh * 16
print("end", r.p, len(d))
