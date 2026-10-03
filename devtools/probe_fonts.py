import re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import game_path
from core.bundle import read_bundle

GAME = game_path("content", "content0", "bundles", "r4gui.bundle")
W3TU = r"C:\Users\saetanpee\Downloads\w3tu\Tools"

game = {f.path: f.data for f in read_bundle(GAME)}
g = game["gameplay\\gui_new\\swf\\witcher3\\fonts_en.redswf"]


def names(data):
    return sorted(set(m.decode() for m in re.findall(rb"\$?[A-Za-z][A-Za-z0-9_ \-]{3,40}", data)
                      if b"font" in m.lower() or b"$" in m[:1]))


print("game fonts_en", len(g), g[:12])
gn = names(g)
print(" game names:", gn[:60])
for mod in sorted(os.listdir(W3TU)):
    if not mod.startswith("modFont"):
        continue
    fs = read_bundle(os.path.join(W3TU, mod, "content", "blob0.bundle"))
    for f in fs:
        mn = names(f.data)
        print(mod, f.path, len(f.data), f.data[:8], "CR2W ver", int.from_bytes(f.data[4:8], "little"))
        print("  missing vs game:", [n for n in gn if n not in mn][:30])
        print("  extra:", [n for n in mn if n not in gn][:30])
st = read_bundle(os.path.join(W3TU, "modThaiStoryBook", "content", "blob0.bundle"))
print("storybook files", len(st), st[0].path, st[0].data[:80])
