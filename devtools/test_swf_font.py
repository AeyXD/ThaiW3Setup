import os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image
from core.assets import font_files
from core.options import FONTS
from core.swf_font import best_font, load_fonts, render_line

TEXT = "\u0e40\u0e01\u0e23\u0e2d\u0e25\u0e17\u0e4c: \u0e02\u0e49\u0e32\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e21\u0e32\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e40\u0e25\u0e48\u0e19  [Geralt: Not here to play]"
out = os.path.join(tempfile.gettempdir(), "w3thai_preview")
os.makedirs(out, exist_ok=True)
rows = []
for name in FONTS:
    t0 = time.time()
    fonts = load_fonts(font_files(name)[0].data)
    f = best_font(fonts, TEXT)
    img = render_line(f, TEXT, 30, (255, 255, 255))
    print(name, [(x.name, len(x.glyphs)) for x in fonts][:6], "->", f.name, img.size, round(time.time() - t0, 2), "s")
    rows.append(img)
W = max(r.width for r in rows) + 20
sheet = Image.new("RGBA", (W, sum(r.height + 8 for r in rows) + 10), (20, 20, 24, 255))
y = 5
for r in rows:
    sheet.alpha_composite(r, (10, y))
    y += r.height + 8
sheet.save(os.path.join(out, "all.png"))
print(os.path.join(out, "all.png"))
