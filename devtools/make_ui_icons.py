"""Generate assets/icons/*.png from Google's Material Symbols (Apache 2.0); run once, the PNGs are committed."""
import os
import re
import tempfile
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

BASE = "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
FONT = "MaterialSymbolsRounded[FILL,GRAD,opsz,wght]"
ICONS = ("update", "bug_report", "folder_open", "download", "expand_more", "drive_file_move", "delete",
         "open_in_new")
SIZE = 48
SCALE = 4
COLOR = (51, 51, 51, 255)

out_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
cache = os.path.join(tempfile.gettempdir(), "material_symbols")


def fetch(name: str) -> str:
    path = os.path.join(cache, name)
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        urllib.request.urlretrieve(BASE + urllib.parse.quote(name), path)
    return path


font_path = fetch(FONT + ".ttf")
with open(fetch(FONT + ".codepoints"), encoding="utf-8") as fh:
    codepoints = dict(re.findall(r"^(\S+) ([0-9a-f]+)$", fh.read(), re.MULTILINE))

big = SIZE * SCALE
font = ImageFont.truetype(font_path, big)
os.makedirs(out_dir, exist_ok=True)
for name in ICONS:
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((big / 2, big / 2), chr(int(codepoints[name], 16)), font=font, fill=COLOR, anchor="mm")
    path = os.path.join(out_dir, f"{name}.png")
    img.resize((SIZE, SIZE), Image.LANCZOS).save(path, optimize=True)
    print("wrote", os.path.abspath(path))
