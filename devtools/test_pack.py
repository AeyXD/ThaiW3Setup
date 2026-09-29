"""Repack a w3tu bundle to v5 + metadata.store v7 and parse the result back."""
import os, sys, struct, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, r"C:\Users\saetanpee\AppData\Local\Temp\w3thai_baseline")
from core.bundle import read_bundle, write_bundle
from core.metastore import build_metastore, BundleLayout
from probe_meta import R

SRC = sys.argv[1]
out = tempfile.mkdtemp()
files = read_bundle(SRC)
size, off, entries = write_bundle(os.path.join(out, "blob0.bundle"), files)
meta = build_metastore(BundleLayout("blob0.bundle", size, off, entries))
open(os.path.join(out, "metadata.store"), "wb").write(meta)

back = read_bundle(os.path.join(out, "blob0.bundle"))
assert [(f.path, f.data) for f in back] == [(f.path, f.data) for f in files], "bundle roundtrip mismatch"
print("bundle ok:", len(files), "files", size, "bytes, data offset", off)

d = meta
r = R(d); r.take(4); print("meta ver/max", r.u32(), r.u32(), r.u32())
st = r.vlq(); strtab = d[r.p:r.p + st]; r.p += st
def rd(fmt, w):
    n = r.vlq(); v = [struct.unpack_from(fmt, d, r.p + i * w) for i in range(n)]; r.p += n * w; return v
fi = rd("<8I", 32); fe = rd("<QIIII", 24); bi = rd("<QIIII", 24); bf = rd("<I", 4)
di = rd("<2i", 8); fin = rd("<3i", 12); hs = rd("<QQ", 16)
assert r.p == len(d), (r.p, len(d))
print("meta ok:", len(fi) - 1, "files", len(di), "dirs", len(hs), "hashes; bundle", bi[1])
print("sample fi", fi[1], "fe", fe[1])
print("out dir", out)
