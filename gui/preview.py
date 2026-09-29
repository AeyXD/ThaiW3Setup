"""Live subtitle preview rendered with the selected in-game font."""
from __future__ import annotations

from PIL import Image

from core.assets import font_files
from core.options import MODE_DOUBLE, InstallOptions
from core.swf_font import Font, best_font, load_fonts, render_line

SPEAKER_TH = "เกรอลท์"
SPEAKER_EN = "Geralt"
LINE_TH = "หมาป่าไม่ล่าเหยื่อเพียงลำพังหรอก"
LINE_EN = "Wolves never hunt alone."
DEFAULT_COLOR = "#FFFFFF"
SPEAKER_COLOR = "#F8FF56"
BACKGROUND = (22, 24, 28, 255)

_fonts: dict[str, Font] = {}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _font(name: str) -> Font:
    if name not in _fonts:
        _fonts[name] = best_font(load_fonts(font_files(name)[0].data), LINE_TH + LINE_EN)
    return _fonts[name]


def _row(font: Font, parts: list[tuple[str, str]], px: int) -> Image.Image:
    images = [render_line(font, text, px, _rgb(color)) for text, color in parts if text]
    w = sum(i.width for i in images)
    h = max(i.height for i in images)
    row = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for img in images:
        row.alpha_composite(img, (x, h - img.height))
        x += img.width
    return row


def render(opts: InstallOptions, width: int, height: int) -> Image.Image:
    font = _font(opts.font)
    styled = opts.subtitle_style
    c1 = opts.color1 if styled else DEFAULT_COLOR
    c2 = opts.color2 if styled else DEFAULT_COLOR
    s1 = opts.size1 if styled else 28
    s2 = opts.size2 if styled else 28
    speaker_color = SPEAKER_COLOR if styled and opts.speaker_colors else c1

    thai, english = LINE_TH, f"[{SPEAKER_EN}: {LINE_EN}]"
    rows = []
    if opts.mode == MODE_DOUBLE and not opts.thai_first:
        rows.append(_row(font, [(SPEAKER_TH + ": ", speaker_color), (LINE_EN, c1)], s1))
        rows.append(_row(font, [(f"[{LINE_TH}]", c2)], s2))
    else:
        rows.append(_row(font, [(SPEAKER_TH + ": ", speaker_color), (thai, c1)], s1))
        if opts.mode == MODE_DOUBLE:
            rows.append(_row(font, [(english, c2)], s2))

    canvas = Image.new("RGBA", (width, height), BACKGROUND)
    total = sum(r.height for r in rows) + 4 * (len(rows) - 1)
    y = max(4, height - total - 18)
    for r in rows:
        if r.width > width - 16:
            r = r.resize((width - 16, max(1, r.height * (width - 16) // r.width)), Image.LANCZOS)
        canvas.alpha_composite(r, ((width - r.width) // 2, y))
        y += r.height + 4
    return canvas.convert("RGB")
