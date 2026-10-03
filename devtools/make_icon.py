"""Generate packaging/icon.ico (run once; the result is committed)."""
import os
from PIL import Image, ImageDraw, ImageFont

out = os.path.join(os.path.dirname(__file__), "..", "packaging", "icon.ico")
S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, S - 8, S - 8), radius=48, fill=(24, 26, 32, 255), outline=(190, 30, 45, 255), width=10)


def pick(px):
    for name in ("seguisb.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


big, small = pick(110), pick(64)
d.text((S / 2, 100), "W3", font=big, fill=(235, 235, 235, 255), anchor="mm")
d.text((S / 2, 190), "TH", font=small, fill=(230, 60, 70, 255), anchor="mm")
os.makedirs(os.path.dirname(out), exist_ok=True)
img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote", os.path.abspath(out))
