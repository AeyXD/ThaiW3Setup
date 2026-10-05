"""Read the text colour translators paint in a sheet and turn it into the game's <font color> tags.

A word (rich text run) or a whole cell painted in a colour close to one of CATEGORY_COLORS is shown in that
category's colour in the game, so terms read as coming from Combat, Signs, Alchemy, General or Mutation skills.
Black, white and very dark text are the normal colour and get no tag.
"""
from __future__ import annotations

import colorsys
import io
import posixpath
import re
import zipfile
from dataclasses import dataclass
from typing import Iterator
from xml.etree.ElementTree import iterparse, parse

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
NS_DRAW = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

COMBAT, SIGNS, ALCHEMY, GENERAL, MUTATION = "combat", "signs", "alchemy", "general", "mutation"
# colours shown in the game, picked to read well on the dark panels
CATEGORY_COLORS = {
    COMBAT: "#c8463a",
    SIGNS: "#4a90d9",
    ALCHEMY: "#6fb043",
    GENERAL: "#d9a82e",
    MUTATION: "#a8a196",
}
# hue (degrees) a painted colour is matched against; grey goes to MUTATION separately
CATEGORY_HUES = ((COMBAT, 0.0), (GENERAL, 45.0), (ALCHEMY, 120.0), (SIGNS, 220.0), (COMBAT, 360.0))

FONT_TAG = re.compile(r"<\s*font", re.IGNORECASE)
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def category(rgb: str | None) -> str | None:
    """Category of a painted colour ("RRGGBB" or "AARRGGBB"); None for the normal text colour."""
    if not rgb:
        return None
    try:
        r, g, b = (int(rgb[-6:][i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return None
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.3:
        return None
    if s < 0.15:
        return MUTATION if v < 0.9 else None
    hue = h * 360
    return min(CATEGORY_HUES, key=lambda c: abs(c[1] - hue))[0]


def snap(rgb: str | None) -> str | None:
    """Game colour ("#rrggbb") for a painted colour; None for the normal text colour."""
    cat = category(rgb)
    return CATEGORY_COLORS[cat] if cat else None


def tag_runs(runs: list[tuple[str, str | None]]) -> str:
    """Join (text, painted rgb) runs, wrapping each stretch of one category in <font color>.
    Spaces between two runs of one colour do not split the tag; leading and trailing spaces stay outside."""
    segs: list[list] = []
    for text, rgb in runs:
        if not text:
            continue
        color = snap(rgb)
        if not text.strip() and segs:
            color = segs[-1][1]
        if segs and segs[-1][1] == color:
            segs[-1][0] += text
        else:
            segs.append([text, color])
    out = []
    for text, color in segs:
        if not color or not text.strip() or FONT_TAG.search(text):
            out.append(text)
            continue
        core = text.strip()
        start = text.index(core)
        out.append(f'{text[:start]}<font color="{color}">{core}</font>{text[start + len(core):]}')
    return "".join(out)


@dataclass
class Cell:
    text: str  # plain text, as openpyxl would read it
    tagged: str  # text with <font color> tags for painted runs


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _number_text(value: str) -> str:
    try:
        f = float(value)
    except ValueError:
        return value
    return str(int(f)) if f.is_integer() else str(f)


def _apply_tint(rgb: str, tint: float) -> str:
    r, g, b = (int(rgb[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l * (1 + tint) if tint < 0 else l * (1 - tint) + tint
    return "".join(f"{round(c * 255):02X}" for c in colorsys.hls_to_rgb(h, l, s))


class ColorWorkbook:
    """Just enough of an xlsx reader to get cell text with its painted colours, streaming the sheets."""

    def __init__(self, data: bytes):
        self._zip = zipfile.ZipFile(io.BytesIO(data))
        self._names = set(self._zip.namelist())
        self._theme = self._read_theme()
        self._xf_colors = self._read_styles()
        self._shared = self._read_shared()
        self._sheets = self._read_sheets()

    @property
    def sheetnames(self) -> list[str]:
        return [name for name, _ in self._sheets]

    def close(self) -> None:
        self._zip.close()

    def _xml(self, name: str):
        return parse(self._zip.open(name)).getroot() if name in self._names else None

    def _read_theme(self) -> list[str]:
        root = self._xml("xl/theme/theme1.xml")
        scheme = root.find(f".//{NS_DRAW}clrScheme") if root is not None else None
        out = []
        for child in list(scheme) if scheme is not None else []:
            srgb = child.find(f"{NS_DRAW}srgbClr")
            sys_ = child.find(f"{NS_DRAW}sysClr")
            out.append(srgb.get("val") if srgb is not None else sys_.get("lastClr", "") if sys_ is not None else "")
        # theme indexes 0-3 are light 1, dark 1, light 2, dark 2 while the scheme lists dark first
        if len(out) >= 4:
            out[0], out[1], out[2], out[3] = out[1], out[0], out[3], out[2]
        return out

    def _color(self, el) -> str | None:
        if el is None:
            return None
        rgb = el.get("rgb")
        if rgb is None and el.get("theme") is not None:
            idx = int(el.get("theme"))
            rgb = self._theme[idx] if idx < len(self._theme) else None
        if not rgb:
            return None
        rgb = rgb[-6:].upper()
        tint = float(el.get("tint") or 0)
        return _apply_tint(rgb, tint) if tint else rgb

    def _read_styles(self) -> list[str | None]:
        root = self._xml("xl/styles.xml")
        if root is None:
            return []
        fonts = [self._color(f.find(f"{NS}color")) for f in root.iterfind(f"{NS}fonts/{NS}font")]
        out = []
        for xf in root.iterfind(f"{NS}cellXfs/{NS}xf"):
            fid = int(xf.get("fontId") or 0)
            out.append(fonts[fid] if fid < len(fonts) else None)
        return out

    def _runs(self, si) -> list[tuple[str, str | None]]:
        """Runs of an <si> or <is>: (text, colour or None to use the cell's)."""
        runs = []
        for r in si.iterfind(f"{NS}r"):
            t = r.find(f"{NS}t")
            rpr = r.find(f"{NS}rPr")
            color = self._color(rpr.find(f"{NS}color")) if rpr is not None else None
            runs.append((t.text or "" if t is not None else "", color))
        if not runs:
            t = si.find(f"{NS}t")
            runs.append((t.text or "" if t is not None else "", None))
        return runs

    def _read_shared(self) -> list[list[tuple[str, str | None]]]:
        name = "xl/sharedStrings.xml"
        if name not in self._names:
            return []
        out = []
        for _, el in iterparse(self._zip.open(name)):
            if el.tag == f"{NS}si":
                out.append(self._runs(el))
                el.clear()
        return out

    def _read_sheets(self) -> list[tuple[str, str]]:
        rels = self._xml("xl/_rels/workbook.xml.rels")
        targets = {}
        for rel in rels.iterfind(f"{NS_PKG_REL}Relationship") if rels is not None else []:
            target = rel.get("Target", "")
            targets[rel.get("Id")] = target.lstrip("/") if target.startswith("/") else posixpath.normpath(
                posixpath.join("xl", target))
        wb = self._xml("xl/workbook.xml")
        return [(s.get("name"), targets.get(s.get(f"{NS_REL}id"), ""))
                for s in wb.iterfind(f"{NS}sheets/{NS}sheet")]

    def rows(self, sheet: str | int = 0, min_row: int = 1, max_col: int | None = None,
             cell_colors: bool = True) -> Iterator[tuple[int, dict[int, Cell]]]:
        """(1-based row number, {0-based column: Cell}) for rows from min_row, empty cells left out.
        With cell_colors off only colours painted on part of a cell count, not a colour of the whole cell."""
        if isinstance(sheet, int):
            path = self._sheets[sheet][1]
        else:
            path = dict(self._sheets)[sheet]
        row_num, cells = 0, {}
        for _, el in iterparse(self._zip.open(path)):
            tag = el.tag
            if tag == f"{NS}c":
                m = CELL_REF.match(el.get("r") or "")
                if m:
                    row_num = int(m.group(2))
                    col = col_index(m.group(1))
                else:
                    col = max(cells, default=-1) + 1
                if row_num >= min_row and (max_col is None or col < max_col):
                    cell = self._cell(el, cell_colors)
                    if cell is not None:
                        cells[col] = cell
                el.clear()
            elif tag == f"{NS}row":
                num = int(el.get("r") or row_num)
                if cells and num >= min_row:
                    yield num, cells
                row_num, cells = num, {}
                el.clear()

    def _cell(self, el, cell_colors: bool = True) -> Cell | None:
        kind = el.get("t", "n")
        xf = int(el.get("s") or 0)
        cell_color = self._xf_colors[xf] if cell_colors and xf < len(self._xf_colors) else None
        v = el.find(f"{NS}v")
        if kind == "s":
            if v is None or not v.text:
                return None
            runs = self._shared[int(v.text)]
        elif kind == "inlineStr":
            inline = el.find(f"{NS}is")
            if inline is None:
                return None
            runs = self._runs(inline)
        elif v is None or v.text is None:
            return None
        elif kind == "n":
            runs = [(_number_text(v.text), None)]
        elif kind == "b":
            runs = [("True" if v.text == "1" else "False", None)]
        else:
            runs = [(v.text, None)]
        runs = [(text, color or cell_color) for text, color in runs]
        text = "".join(t for t, _ in runs)
        if not text:
            return None
        return Cell(text, tag_runs(runs))
