import glob, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.bundle import read_bundle
from core.sheet import get_translations
from core.assets import GLYPH_ALIASES
from core.swf_font import add_empty_glyph, alias_glyphs, load_fonts
from core.text_builder import combine
from core.thai_wrap import BREAK, NBSP, NO_BREAK_AFTER, NO_BREAK_BEFORE, YAMOK_SPACE, ThaiWrapper, load_words

w = ThaiWrapper(load_words())


def cut(text):
    return w.wrap(text).replace(BREAK, "|")


assert cut("เมื่อมนุษย์บุกลุกดินแดนของพวกมัน") == "เมื่อ|มนุษย์|บุก|ลุก|ดินแดน|ของ|พวก|มัน", cut("เมื่อมนุษย์บุกลุกดินแดนของพวกมัน")
assert cut("คุณไม่มีระเบิดที่ใช้ได้") == "คุณ|ไม่มี|ระเบิด|ที่|ใช้ได้"
assert cut("กับทริสส์") == "กับ|ทริสส์"  # unknown name stays whole
w.add_words(["เยนเนเฟอร์"])
assert cut("เยนเนเฟอร์กับ") == "เยนเนเฟอร์|กับ"
assert w.wrap("Points available") == "Points available"
assert w.wrap("") == ""
tagged = "ครึ่งอินทรี</i><br>– Griffin <font color='#CD7'>โจมตีผู้พบเห็น</font>  [Aye]"
out = w.wrap(tagged)
assert out.replace(BREAK, "") == tagged
assert "</i><br>" in out and "<font color='#CD7'>" in out and "  [Aye]" in out
for i, c in enumerate(out):
    if c == BREAK:
        assert "\u0e01" <= out[i - 1] <= "\u0e4e" and "\u0e01" <= out[i + 1] <= "\u0e4e"
        assert out[i + 1] not in NO_BREAK_BEFORE and out[i - 1] not in NO_BREAK_AFTER

# ไม้ยมก: the standard's space before ๆ must not be a line-break opportunity; the space after it still is
assert w.wrap("ต่าง ๆ นานา").replace(BREAK, "|") == "ต่าง" + NBSP + "ๆ นานา"
assert w.wrap("เร็ว ๆๆ!") == "เร็ว" + NBSP + "ๆๆ!"
assert w.wrap("จริง  ๆ") == "จริง" + NBSP + "ๆ"
assert NBSP not in w.wrap("ๆ ต้นข้อความ") and NBSP not in w.wrap("ไม่มี ไม้ยมก")

assert combine("ไทย", "English", True) == "ไทย  [English]"
assert combine("ไทย<br>ต่อ", "English<br>more", True) == "ไทย<br>ต่อ<br><br>[English<br>more]"
assert combine("ไทย<BR>ต่อ", "English", False) == "English<br><br>[ไทย<BR>ต่อ]"

for path in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "*.bundle"))):
    data = [f.data for f in read_bundle(path) if f.path.endswith("fonts_en.redswf")][0]
    fonts = load_fonts(add_empty_glyph(data, ord(BREAK)))
    for f in fonts:
        g = f.glyphs[ord(BREAK)]
        assert f.advances[g] == 0 and not f.contours(g), path
    assert add_empty_glyph(add_empty_glyph(data, ord(BREAK)), ord(BREAK)) == add_empty_glyph(data, ord(BREAK))
    aliased = alias_glyphs(add_empty_glyph(data, ord(BREAK)), GLYPH_ALIASES)
    assert alias_glyphs(aliased, GLYPH_ALIASES) == aliased
    for before, f in zip(fonts, load_fonts(aliased)):
        added = {c for c, target in GLYPH_ALIASES.items() if target in before.glyphs}
        assert set(f.glyphs) == set(before.glyphs) | added, path
        for code, target in GLYPH_ALIASES.items():
            if target in f.glyphs:
                a, b = f.glyphs[code], f.glyphs[target]
                assert f.shapes[a] == f.shapes[b] and f.advances[a] == f.advances[b], (path, hex(code))
        for code, gi in before.glyphs.items():
            if code not in GLYPH_ALIASES:
                assert f.shapes[f.glyphs[code]] == before.shapes[gi], (path, hex(code))

tr = get_translations(allow_online=False)
texts = list(tr.thai.values())
t0 = time.time()
wrapped = [ThaiWrapper(load_words()).wrap(t) for t in texts[:1]] + [w.wrap(t) for t in texts]
dt = time.time() - t0
assert all(a.replace(BREAK, "") == YAMOK_SPACE.sub(NBSP, b) for a, b in zip(wrapped[1:], texts))
print(f"wrapped {len(texts):,} strings in {dt:.1f}s, {sum(t.count(BREAK) for t in wrapped):,} breaks")
print("test_thai_wrap ok")
