"""Live subtitle preview rendered with the selected in-game font."""
from __future__ import annotations

from PIL import Image

from core.assets import font_files
from core.options import MODE_DOUBLE, InstallOptions
from core.swf_font import EM, Font, best_font, load_fonts, render_line, text_width

SPEAKER_TH = "เกรอลท์"
SPEAKER_EN = "Geralt"
# Zero-width spaces mark word breaks for wrapping; they are not drawn.
LINE_TH = ("\u0e2b\u0e21\u0e32\u0e1b\u0e48\u0e32\u200b\u0e44\u0e21\u0e48\u200b\u0e25\u0e48\u0e32\u200b"
           "\u0e40\u0e2b\u0e22\u0e37\u0e48\u0e2d\u200b\u0e40\u0e1e\u0e35\u0e22\u0e07\u200b"
           "\u0e25\u0e33\u0e1e\u0e31\u0e07\u200b\u0e2b\u0e23\u0e2d\u0e01")
ZWSP = "\u200b"
# baseline-to-baseline distance per pixel of font size, measured in game (50 px for size 46)
LINE_PITCH = 1.08
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
        _fonts[name] = best_font(load_fonts(font_files(name)[0].data), LINE_TH.replace(ZWSP, "") + LINE_EN)
    return _fonts[name]


def _row(font: Font, parts: list[tuple[str, str]], px: int) -> Image.Image:
    parts = [(text.replace(ZWSP, ""), color) for text, color in parts]
    images = [render_line(font, text, px, _rgb(color)) for text, color in parts if text]
    w = sum(i.width for i in images)
    h = max(i.height for i in images)
    row = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for img in images:
        row.alpha_composite(img, (x, h - img.height))
        x += img.width
    return row


THAI_ATTACH_PREV = {0x0E30, 0x0E31, 0x0E32, 0x0E33, 0x0E45, 0x0E46} | set(range(0x0E34, 0x0E3B)) \
    | set(range(0x0E47, 0x0E4F))
THAI_LEADING = set(range(0x0E40, 0x0E45))


def _clusters(word: str) -> list[str]:
    """Split into pieces that may be broken between: marks and trailing vowels stay with their
    consonant, leading vowels stay with the next one."""
    out: list[str] = []
    for c in word:
        if out and (ord(c) in THAI_ATTACH_PREV or ord(out[-1][-1]) in THAI_LEADING):
            out[-1] += c
        else:
            out.append(c)
    return out


def _wrap(font: Font, parts: list[tuple[str, str]], px: int, max_width: float) -> list[list[tuple[str, str]]]:
    tokens: list[tuple[str, str]] = []
    for text, color in parts:
        words = text.split(" ")
        for word in [w + " " for w in words[:-1]] + [words[-1]]:
            tokens += [(t, color) for t in word.split(ZWSP)]
    lines: list[list[tuple[str, str]]] = [[]]
    width = 0.0

    def put(text, color):
        nonlocal width
        w = text_width(font, text, px)
        if width + text_width(font, text.rstrip(), px) > max_width and lines[-1]:
            lines.append([])
            width = 0.0
            if not text.strip():
                return
        lines[-1].append((text, color))
        width += w

    for token, color in tokens:
        if not token:
            continue
        if text_width(font, token.rstrip(), px) <= max_width:
            put(token, color)
        else:
            for piece in _clusters(token):
                put(piece, color)
    merged = []
    for line in lines:
        out: list[tuple[str, str]] = []
        for text, color in line:
            if out and out[-1][1] == color:
                out[-1] = (out[-1][0] + text, color)
            else:
                out.append((text, color))
        if out:
            out[-1] = (out[-1][0].rstrip(), out[-1][1])
        merged.append(out)
    return merged


def subtitle_rows(opts: InstallOptions, scale: float = 1.0, max_width: float | None = None) -> list[Image.Image]:
    return [img for img, _px in _subtitle_lines(opts, scale, max_width)]


def subtitle_block(opts: InstallOptions, scale: float = 1.0, max_width: float | None = None) -> Image.Image:
    """Subtitle lines stacked by baseline the way the game spaces them."""
    font = _font(opts.font)
    lines = _subtitle_lines(opts, scale, max_width)
    desc = [(font.descent or int(EM * 0.3)) * px / EM + 1 for _img, px in lines]
    baselines = [lines[0][0].height - desc[0]]
    for (_img, px) in lines[1:]:
        baselines.append(baselines[-1] + LINE_PITCH * px)
    out = Image.new("RGBA", (max(img.width for img, _ in lines), round(baselines[-1] + desc[-1])), (0, 0, 0, 0))
    for (img, _px), base, d in zip(lines, baselines, desc):
        out.alpha_composite(img, ((out.width - img.width) // 2, max(0, round(base + d - img.height))))
    return out


def _subtitle_lines(opts: InstallOptions, scale: float, max_width: float | None) -> list[tuple[Image.Image, int]]:
    font = _font(opts.font)
    styled = opts.subtitle_style
    c1 = opts.color1 if styled else DEFAULT_COLOR
    c2 = opts.color2 if styled else DEFAULT_COLOR
    s1 = max(8, round((opts.size1 if styled else 28) * scale))
    s2 = max(8, round((opts.size2 if styled else 28) * scale))
    speaker_color = SPEAKER_COLOR if styled and opts.speaker_colors else c1

    thai, english = LINE_TH, f"[{SPEAKER_EN}: {LINE_EN}]"
    rows = []

    def add(parts, px):
        for line in _wrap(font, parts, px, max_width) if max_width else [parts]:
            rows.append((_row(font, line, px), px))

    if opts.mode == MODE_DOUBLE and not opts.thai_first:
        add([(SPEAKER_TH + ": ", speaker_color), (LINE_EN, c1)], s1)
        add([(f"[{LINE_TH}]", c2)], s2)
    else:
        add([(SPEAKER_TH + ": ", speaker_color), (thai, c1)], s1)
        if opts.mode == MODE_DOUBLE:
            add([(english, c2)], s2)
    return rows


def descent_px(opts: InstallOptions, px: float) -> float:
    font = _font(opts.font)
    return (font.descent or int(EM * 0.3)) * px / EM


def text_rows(opts: InstallOptions, text: str, color: str, px: int, max_width: float) -> list[Image.Image]:
    font = _font(opts.font)
    return [_row(font, line, px) for line in _wrap(font, [(text, color)], px, max_width)]


def render(opts: InstallOptions, width: int, height: int) -> Image.Image:
    rows = subtitle_rows(opts)
    canvas = Image.new("RGBA", (width, height), BACKGROUND)
    total = sum(r.height for r in rows) + 4 * (len(rows) - 1)
    y = max(4, height - total - 18)
    for r in rows:
        if r.width > width - 16:
            r = r.resize((width - 16, max(1, r.height * (width - 16) // r.width)), Image.LANCZOS)
        canvas.alpha_composite(r, ((width - r.width) // 2, y))
        y += r.height + 4
    return canvas.convert("RGB")
