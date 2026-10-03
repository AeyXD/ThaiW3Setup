"""Build the HUD layout preview backgrounds in assets/layout_bg.

    python devtools/make_layout_bg.py photo1=<image> photo2=<image>

Images are shrunk to at most 1280x720, get the screenshot credit burned into the
bottom-right corner and are saved as small progressive JPEGs.
"""
import os, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "layout_bg"
MAX_SIZE = (1280, 720)
CREDIT = "Screenshot: MILOGAME_AVIF HDR - eu.zonerama.com/PrestigiousCap4934/Album/16612460"
FONT_CANDIDATES = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
                   "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"]


def _font(px: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def build(src: Path, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    img.thumbnail(MAX_SIZE, Image.LANCZOS)
    font = _font(max(10, round(12 * img.width / 1024)))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    left, top, right, bottom = draw.textbbox((0, 0), CREDIT, font=font)
    pad = 4
    x = img.width - (right - left) - pad * 2 - 6
    y = img.height - (bottom - top) - pad * 2 - 6
    draw.rectangle((x, y, img.width - 6, img.height - 6), fill=(0, 0, 0, 120))
    draw.text((x + pad - left, y + pad - top), CREDIT, font=font, fill=(235, 235, 235, 220))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=80, optimize=True, progressive=True)
    print(dst.name, img.size, dst.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        name, _, path = arg.partition("=")
        build(Path(path), OUT / f"{name}.jpg")
