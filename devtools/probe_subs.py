import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import game_path
from core.bundle import read_bundle

meta = open(game_path("content", "metadata.store"), "rb").read()
names = set(meta.split(b"\0"))
files = read_bundle(r"C:\Users\saetanpee\Downloads\w3tu\Tools\modThaiStoryBook\content\blob0.bundle")
tr_ok = en_ok = 0
missing = []
for f in files:
    p = f.path.encode()
    if p in names:
        tr_ok += 1
    else:
        missing.append(f.path)
    if p.replace(b"_tr.subs", b"_en.subs") in names:
        en_ok += 1
print("storybook files", len(files), "tr path exists", tr_ok, "en path exists", en_ok)
print("missing", missing[:10])
usm = [f.path.replace("\\subs\\", "\\").replace("\\altsubs\\", "\\").rsplit("_", 1)[0] + ".usm" for f in files]
print("usm exist", sum(1 for u in usm if u.encode() in names), "of", len(usm), usm[:2])
