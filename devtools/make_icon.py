"""Generate packaging/icon.ico and, where iconutil exists, packaging/icon.icns (run once; results committed).

The committed icon.ico was drawn on Windows with Segoe UI Semibold; running this anywhere else falls back
to another bold face and rewrites it, so only commit the .ico when you ran this on Windows.
"""
import os
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

PACKAGING = os.path.join(os.path.dirname(__file__), "..", "packaging")
ICO_PX = 256    # what the .ico has always been drawn at; keep it so the Windows icon does not change
ICNS_PX = 1024  # the largest size macOS asks for
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
# every size an .icns carries, as <size>x<size>[@2x]
ICNS_SIZES = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)]


def pick(px):
    for name in ("seguisb.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def draw(px: int) -> Image.Image:
    """The artwork, laid out on a 256 px square and scaled to `px`."""
    k = px / 256
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8 * k, 8 * k, px - 8 * k, px - 8 * k), radius=48 * k,
                        fill=(24, 26, 32, 255), outline=(190, 30, 45, 255), width=round(10 * k))
    d.text((px / 2, 100 * k), "W3", font=pick(round(110 * k)), fill=(235, 235, 235, 255), anchor="mm")
    d.text((px / 2, 190 * k), "TH", font=pick(round(64 * k)), fill=(230, 60, 70, 255), anchor="mm")
    return img


def write_icns(img: Image.Image, out: str) -> None:
    """iconutil wants a folder of PNGs named the way macOS expects."""
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "icon.iconset")
        os.makedirs(iconset)
        for size, scale in ICNS_SIZES:
            suffix = "@2x" if scale == 2 else ""
            img.resize((size * scale, size * scale), Image.LANCZOS).save(
                os.path.join(iconset, f"icon_{size}x{size}{suffix}.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)


os.makedirs(PACKAGING, exist_ok=True)
ico = os.path.join(PACKAGING, "icon.ico")
draw(ICO_PX).save(ico, sizes=ICO_SIZES)
print("wrote", os.path.abspath(ico))

if shutil.which("iconutil"):
    icns = os.path.join(PACKAGING, "icon.icns")
    write_icns(draw(ICNS_PX), icns)
    print("wrote", os.path.abspath(icns))
else:
    print("no iconutil here, skipped icon.icns (run this on macOS to refresh it)")
