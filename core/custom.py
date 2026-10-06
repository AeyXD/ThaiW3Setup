"""Optional id-keyed "custom translation" sheets layered over the main translation (as in w3tu)."""
from __future__ import annotations

import colorsys
import gzip
import hashlib
import io
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field

from .paths import assets_dir, cache_dir
from .progress import ProgressFn, noop, scaled
from .rich_color import ColorWorkbook
from .sheet import CACHE_MAX_AGE, EXPORT_URL, _cell_text, _download

log = logging.getLogger(__name__)

SHEET_URL = "https://docs.google.com/spreadsheets/d/{id}"
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{25,}$")
URL_PATTERN = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]{25,})")


@dataclass
class CustomSheet:
    sheet_id: str
    name: str
    enabled: bool = False
    # worksheet title; empty means the first worksheet
    tab: str = ""
    gid: int | None = None
    # name tabs only: NAME_THAI shows the THAI column, NAME_DOUBLE the "English (Thai)" TRANSLATE column
    name_mode: str = ""


NAME_THAI = "thai"
NAME_DOUBLE = "double"
NAME_MODES = ("", NAME_THAI, NAME_DOUBLE)


@dataclass
class CustomData:
    title: str
    strings: dict[int, str]
    # THAI column (empty for sheets without one) and every id listed in the tab, filled or not
    thai: dict[int, str] = field(default_factory=dict)
    ids: list[int] = field(default_factory=list)
    # ids whose TRANSLATE cell is filled green: checked by the community, including ones left untranslated on purpose
    done: list[int] = field(default_factory=list)
    # ids whose TRANSLATE cell has any other colour than green, yellow or white: left out of the progress
    skipped: list[int] = field(default_factory=list)


@dataclass
class Overrides:
    strings: dict[int, str] = field(default_factory=dict)
    # ids shown in the game's English (name tabs switched off, or no Thai yet)
    keep_english: set[int] = field(default_factory=set)
    # ids never extended with "[English]" in two-language subtitles
    plain: set[int] = field(default_factory=set)
    # ids of name tabs (switched on or off) still without a Thai name: shown in English, not counted as translated
    missing: set[int] = field(default_factory=set)
    # coverage follows progress_of: green rows count as translated even when empty, rows of other colours
    # (in tabs that mark rows green) are left out of the total
    done: set[int] = field(default_factory=set)
    excluded: set[int] = field(default_factory=set)

    def counted(self, sid: int, translated: bool) -> bool:
        return sid not in self.excluded and sid not in self.missing and (translated or sid in self.done)


COMMUNITY_ID = "1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk"
UNTRANSLATED_TAB = "Untranslated"
REWORK_NAME = "ThaiW3 - \u0e1b\u0e23\u0e31\u0e1a\u0e1b\u0e23\u0e38\u0e07\u0e43\u0e2b\u0e21\u0e48"
REWORK_TAB = "\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22 - \u0e23\u0e2d\u0e1b\u0e25\u0e48\u0e2d\u0e22"
TAB_CHARACTERS = "\u0e0a\u0e37\u0e48\u0e2d\u0e15\u0e31\u0e27\u0e25\u0e30\u0e04\u0e23"
TAB_PLACES = "\u0e0a\u0e37\u0e48\u0e2d\u0e40\u0e21\u0e37\u0e2d\u0e07"
TAB_QUESTS = "\u0e0a\u0e37\u0e48\u0e2d\u0e40\u0e04\u0e27\u0e2a"
TAB_SKILLS = "\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e01\u0e34\u0e25"
TAB_MONSTERS = "\u0e0a\u0e37\u0e48\u0e2d\u0e21\u0e2d\u0e19\u0e2a\u0e40\u0e15\u0e2d\u0e23\u0e4c"
TAB_ITEMS = "\u0e0a\u0e37\u0e48\u0e2d\u0e44\u0e2d\u0e40\u0e17\u0e21"
TAB_GWENT = "\u0e0a\u0e37\u0e48\u0e2d\u0e01\u0e32\u0e23\u0e4c\u0e14\u0e40\u0e01\u0e27\u0e19\u0e15\u0e4c"
TAB_OTHER = "\u0e0a\u0e37\u0e48\u0e2d\u0e2d\u0e37\u0e48\u0e19\u0e46"
NAME_TABS = (TAB_CHARACTERS, TAB_PLACES, TAB_QUESTS, TAB_SKILLS, TAB_MONSTERS, TAB_ITEMS, TAB_GWENT, TAB_OTHER)
NAME_GIDS = {TAB_CHARACTERS: 1219926511, TAB_PLACES: 796210995, TAB_QUESTS: 1268129566,
             TAB_SKILLS: 1710767002, TAB_MONSTERS: 1221982709, TAB_ITEMS: 1392156453, TAB_GWENT: 566424687,
             TAB_OTHER: 1610218200}
NAME_LABEL_PREFIX = "\u0e41\u0e1b\u0e25"


def name_label(tab: str) -> str:
    return NAME_LABEL_PREFIX + tab
# entries saved before tabs existed read the first worksheet, which was this one
LEGACY_TABS = {COMMUNITY_ID: UNTRANSLATED_TAB}


# Order matters: sheets lower in the list override those above for the same id.
DEFAULT_SHEETS = [
    CustomSheet("16rgIGMmFzO1GsS-JdNXbkgTRaEma6LOuR_2EF76-TuQ", "ข้อความที่หายไป", True),
    CustomSheet("1X2VOm21x5ow_duSutaXV3AsCdz2YT1RVZZQoiPZHp14", "ชื่อเควสภาษาอังกฤษ"),
    CustomSheet("1eDp6YF3kdx9FXc8dfMFhz72QbH9wYJfKRx2gwvD4Wcg", "ปรับปรุงการแปล"),
    CustomSheet("1FDNdc-p0VJfv3ksoIAhl554jOdpecE6zw6io9tl5jPo", "สุภาพกันหน่อย"),
    CustomSheet("19uVPHxzMBwCxpnjKqakNkBqxSOm2CH173L4wpwiUjS0", "ซับนรก"),
    # "community additions": strings with no translation yet, see devtools/export_untranslated.py
    CustomSheet(COMMUNITY_ID,
                "\u0e04\u0e33\u0e41\u0e1b\u0e25\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e40\u0e15\u0e34\u0e21\u0e08\u0e32\u0e01\u0e0a\u0e38\u0e21\u0e0a\u0e19", True,
                UNTRANSLATED_TAB, 0),
    # proper names shown as "English (Thai)", see devtools/export_names.py
    *(CustomSheet(COMMUNITY_ID, name_label(tab), True, tab, NAME_GIDS.get(tab), NAME_DOUBLE) for tab in NAME_TABS),
]

# unlocked by typing UNLOCK_CODE in the custom sheets dialog; move into DEFAULT_SHEETS once released
HIDDEN_SHEETS = [
    # every English string, retranslated from scratch, see devtools/import_en_csv.py
    CustomSheet("126vDT8d3oQkt_-XsLT8Ii1bTu-ZdrxHKHvMXgT5AGSc",
                REWORK_NAME + " (\u0e23\u0e2d\u0e1b\u0e25\u0e48\u0e2d\u0e22)", True, REWORK_TAB, 0),
]
UNLOCK_CODE = "w3beta"


def is_name_tab(sheet: dict) -> bool:
    return sheet.get("sheet_id") == COMMUNITY_ID and sheet.get("tab") in NAME_TABS


def sheet_key(sheet: dict) -> str:
    tab = sheet.get("tab") or ""
    return f"{sheet['sheet_id']}#{tab}" if tab else sheet["sheet_id"]


def default_sheets() -> list[dict]:
    return [asdict(s) for s in DEFAULT_SHEETS]


def name_settings(sheets: list[dict]) -> tuple[set[str], str]:
    """(switched-on name tabs, the name mode they share); the mode is empty when the tabs differ."""
    tabs = [s for s in sheets if is_name_tab(s)]
    modes = {s.get("name_mode") or NAME_DOUBLE for s in tabs}
    return {s["tab"] for s in tabs if s.get("enabled")}, modes.pop() if len(modes) == 1 else ""


def name_modes(sheets: list[dict]) -> dict[str, str]:
    """Name mode of every name tab, removed tabs as the default."""
    modes = {tab: NAME_DOUBLE for tab in NAME_TABS}
    modes.update({s["tab"]: s.get("name_mode") or NAME_DOUBLE for s in sheets if is_name_tab(s)})
    return modes


def apply_name_settings(sheets: list[dict], enabled: set[str], mode: str | dict[str, str]) -> list[dict]:
    """Copy of sheets with the name tabs switched to enabled. mode is one mode for every tab or one per tab;
    an empty mode keeps the tab's own. A tab removed from the list comes back when switched on."""
    def mode_of(tab: str) -> str:
        return mode.get(tab, "") if isinstance(mode, dict) else mode

    out = [dict(s) for s in sheets]
    have = set()
    for s in out:
        if is_name_tab(s):
            have.add(s["tab"])
            s["enabled"] = s["tab"] in enabled
            if mode_of(s["tab"]):
                s["name_mode"] = mode_of(s["tab"])
    for s in default_sheets():
        if is_name_tab(s) and s["tab"] in enabled and s["tab"] not in have:
            out.append(dict(s, enabled=True, name_mode=mode_of(s["tab"]) or NAME_DOUBLE))
    return out


def hidden_sheets() -> list[dict]:
    return [asdict(s) for s in HIDDEN_SHEETS]


def parse_sheet_id(text: str) -> str | None:
    text = text.strip()
    m = URL_PATTERN.search(text)
    if m:
        return m.group(1)
    return text if ID_PATTERN.match(text) else None


def sheet_url(sheet_id: str, gid: int | None = None) -> str:
    url = SHEET_URL.format(id=sheet_id)
    return f"{url}/edit#gid={gid}" if gid is not None else url


def _ids(cell: str) -> list[int]:
    """One id, or several separated by commas (one row per name covering all its string ids)."""
    out = []
    for part in cell.split(","):
        try:
            out.append(int(float(part)))
        except ValueError:
            pass
    return out


FILL_NONE, FILL_GREEN, FILL_OTHER = "none", "green", "other"


def _fill_kind(cell) -> str:
    """FILL_NONE for no fill, white or yellow; FILL_GREEN; FILL_OTHER for any other colour (grey, orange, blue...)."""
    fill = getattr(cell, "fill", None)
    if fill is None or not fill.fill_type or fill.fgColor is None:
        return FILL_NONE
    if fill.fgColor.type != "rgb":
        return FILL_OTHER
    try:
        rgb = str(fill.fgColor.rgb)[-6:]
        h, s, v = colorsys.rgb_to_hsv(*(int(rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    except ValueError:
        return FILL_OTHER
    if s < 0.1:
        return FILL_NONE if v >= 0.95 else FILL_OTHER
    hue = h * 360
    if 40 <= hue < 70:
        return FILL_NONE
    return FILL_GREEN if 70 <= hue < 170 else FILL_OTHER


def parse_custom_xlsx(data: bytes, tab: str = "") -> CustomData:
    """Worksheet ``tab`` (or the first): a title row, a header row with ID and TRANSLATE (and optionally
    THAI), then data rows. TRANSLATE and THAI keep the category colours painted on their text (see rich_color)."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    if tab and tab not in wb.sheetnames:
        wb.close()
        raise ValueError(f"\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e41\u0e17\u0e47\u0e1a \"{tab}\" \u0e43\u0e19 sheet")
    ws = wb[tab] if tab else wb.worksheets[0]
    colored_wb = ColorWorkbook(data)
    colored = dict(colored_wb.rows(tab or 0))
    colored_wb.close()
    title, id_col, tr_col, th_col = "", None, None, None
    out = CustomData("", {})
    for i, styled in enumerate(ws.iter_rows()):
        row = [c.value for c in styled]
        cells = [_cell_text(c).strip() for c in row]
        if id_col is None:
            if i == 0 and cells:
                title = cells[0]
            upper = [c.upper() for c in cells]
            if "ID" in upper and "TRANSLATE" in upper:
                id_col, tr_col = upper.index("ID"), upper.index("TRANSLATE")
                th_col = upper.index("THAI") if "THAI" in upper else None
            elif i > 10:
                break
            continue
        if len(cells) <= id_col:
            continue
        ids = _ids(cells[id_col])
        out.ids.extend(ids)
        kind = _fill_kind(styled[tr_col]) if len(styled) > tr_col else FILL_NONE
        if kind == FILL_GREEN:
            out.done.extend(ids)
        elif kind == FILL_OTHER:
            out.skipped.extend(ids)
        row_num = next((c.row for c in styled if getattr(c, "row", None)), None)
        tagged = colored.get(row_num, {})
        if th_col is not None and len(cells) > th_col and cells[th_col]:
            th = tagged[th_col].tagged.strip() if th_col in tagged else cells[th_col]
            for sid in ids:
                out.thai[sid] = th
        if len(cells) > tr_col and cells[tr_col]:
            tr = tagged[tr_col].tagged if tr_col in tagged else _cell_text(row[tr_col])
            for sid in ids:
                out.strings[sid] = tr
    wb.close()
    if id_col is None:
        raise ValueError("ไม่พบหัวตาราง ID / TRANSLATE ในแท็บแรกของ sheet")
    out.title = title
    return out


def _file_stem(sheet_id: str, tab: str) -> str:
    if not tab or LEGACY_TABS.get(sheet_id) == tab:
        return sheet_id
    return f"{sheet_id}__{hashlib.sha1(tab.encode('utf-8')).hexdigest()[:8]}"


def _cache_path(sheet_id: str, tab: str = ""):
    return cache_dir() / f"custom_{_file_stem(sheet_id, tab)}.json.gz"


def _bundled_path(sheet_id: str, tab: str = ""):
    return assets_dir() / "custom" / f"{_file_stem(sheet_id, tab)}.json.gz"


# 2: TRANSLATE / THAI carry <font color> tags for painted category colours
CUSTOM_FORMAT = 2


def save_custom(path, data: CustomData, fetched_at: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"format": CUSTOM_FORMAT, "title": data.title, "fetched_at": fetched_at,
                   "strings": {str(k): v for k, v in data.strings.items()},
                   "thai": {str(k): v for k, v in data.thai.items()},
                   "ids": data.ids, "done": data.done, "skipped": data.skipped}, fh, ensure_ascii=False)


def load_custom(path) -> tuple[CustomData, float, bool]:
    """The flag is False for files of an older CUSTOM_FORMAT (no THAI and ids, or no category colours)."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    data = CustomData(payload.get("title", ""), {int(k): v for k, v in payload["strings"].items()},
                      {int(k): v for k, v in payload.get("thai", {}).items()},
                      [int(k) for k in payload.get("ids", [])], [int(k) for k in payload.get("done", [])],
                      [int(k) for k in payload.get("skipped", [])])
    return data, float(payload["fetched_at"]), payload.get("format") == CUSTOM_FORMAT


def _fetch(sheet_id: str, progress: ProgressFn, pool: dict[str, bytes] | None) -> bytes:
    """The xlsx export holds every tab, so tabs of one sheet share a download through ``pool``."""
    if pool is not None and sheet_id in pool:
        return pool[sheet_id]
    data = _download(EXPORT_URL.format(id=sheet_id), progress)
    if pool is not None:
        pool[sheet_id] = data
    return data


def download_custom(sheet_id: str, tab: str = "", progress: ProgressFn = noop,
                    pool: dict[str, bytes] | None = None) -> CustomData:
    data = parse_custom_xlsx(_fetch(sheet_id, progress, pool), tab)
    save_custom(_cache_path(sheet_id, tab), data, time.time())
    return data


def progress_of(data: CustomData) -> float | None:
    """Share of the ids listed in the tab that are done; None when the ids are unknown. In a tab that marks
    rows green only green rows are done and rows of other colours (not yellow or white) are left out;
    otherwise every id with a translation counts."""
    ids = set(data.ids)
    if data.done:
        ids -= set(data.skipped)
    if not ids:
        return None
    done = set(data.done) if data.done else set(data.strings)
    return len(ids & done) / len(ids)


def cached_stats(sheet_id: str, tab: str = "") -> tuple[int | None, float | None]:
    """(translated strings, progress_of) from the cache or the bundled snapshot."""
    for path in (_cache_path(sheet_id, tab), _bundled_path(sheet_id, tab)):
        if path.exists():
            try:
                data = load_custom(path)[0]
                return len(data.strings), progress_of(data)
            except (OSError, ValueError, KeyError):
                pass
    return None, None


def cached_thai_name(tab: str, english: str) -> str | None:
    """Thai of a name in a community name tab, from the cache or the bundled snapshot."""
    prefix = f"{english} ("
    for path in (_cache_path(COMMUNITY_ID, tab), _bundled_path(COMMUNITY_ID, tab)):
        if path.exists():
            try:
                data = load_custom(path)[0]
            except (OSError, ValueError, KeyError):
                continue
            for sid, text in data.strings.items():
                if text.startswith(prefix) and data.thai.get(sid):
                    return data.thai[sid]
    return None


def get_custom_data(sheet_id: str, force_download: bool = False, allow_online: bool = True,
                    progress: ProgressFn = noop, tab: str = "",
                    pool: dict[str, bytes] | None = None) -> CustomData:
    cache = _cache_path(sheet_id, tab)
    if cache.exists() and not force_download:
        try:
            data, ts, complete = load_custom(cache)
            fresh = time.time() - ts < CACHE_MAX_AGE and complete
            if fresh or not allow_online:
                return data
        except (OSError, ValueError, KeyError) as exc:
            log.warning("custom cache %s unreadable: %s", sheet_id, exc)
    if allow_online:
        try:
            return download_custom(sheet_id, tab, progress, pool)
        except Exception as exc:  # network errors come in many types
            log.warning("custom sheet %s %s download failed: %s", sheet_id, tab, exc)
    for path in (cache, _bundled_path(sheet_id, tab)):
        if path.exists():
            try:
                return load_custom(path)[0]
            except (OSError, ValueError, KeyError) as exc:
                log.warning("%s unreadable: %s", path, exc)
    log.warning("custom sheet %s unavailable, skipped", sheet_id)
    return CustomData("", {})


def get_custom(sheet_id: str, force_download: bool = False, allow_online: bool = True,
               progress: ProgressFn = noop, tab: str = "",
               pool: dict[str, bytes] | None = None) -> dict[int, str]:
    return get_custom_data(sheet_id, force_download, allow_online, progress, tab, pool).strings


def merged_overrides(sheets: list[dict], force_download: bool = False,
                     progress: ProgressFn = noop) -> Overrides:
    """Merge enabled sheets top to bottom; later sheets win. Name tabs are read even when switched off:
    their ids then stay English."""
    enabled = [s for s in sheets if s.get("enabled") or is_name_tab(s)]
    out = Overrides()
    pool: dict[str, bytes] = {}
    for i, s in enumerate(enabled):
        progress(i / max(1, len(enabled)), f"คำแปลเสริม: {s.get('name') or s['sheet_id']}")
        data = get_custom_data(s["sheet_id"], force_download,
                               progress=scaled(progress, i / len(enabled), (i + 1) / len(enabled)),
                               tab=s.get("tab") or "", pool=pool)
        if is_name_tab(s):
            _apply_name_tab(out, data, (s.get("name_mode") or NAME_DOUBLE) if s.get("enabled") else "")
        else:
            out.strings.update(data.strings)
            out.keep_english.difference_update(data.strings)
            out.missing.difference_update(data.strings)
            out.excluded.difference_update(data.strings)
        _apply_marks(out, data)
    progress(1.0, "โหลดคำแปลเสริมแล้ว")
    return out


def _apply_marks(out: Overrides, data: CustomData) -> None:
    """Row colours of one sheet, as progress_of reads them: only tabs with green rows mark anything."""
    if not data.done:
        return
    out.done.update(data.done)
    out.excluded.difference_update(data.done)
    out.missing.difference_update(data.done)
    out.excluded.update(data.skipped)
    out.done.difference_update(data.skipped)


def _apply_name_tab(out: Overrides, data: CustomData, mode: str) -> None:
    """mode is NAME_THAI or NAME_DOUBLE for a switched-on tab, empty for a switched-off one."""
    shown = data.thai if mode == NAME_THAI else data.strings if mode == NAME_DOUBLE else {}
    for sid in set(data.ids) | set(data.strings) | set(data.thai):
        out.plain.add(sid)
        if shown.get(sid):
            out.strings[sid] = shown[sid]
            out.keep_english.discard(sid)
            out.missing.discard(sid)
        else:
            out.strings.pop(sid, None)
            out.keep_english.add(sid)
            if mode or not (data.thai.get(sid) or data.strings.get(sid)):
                out.missing.add(sid)
            else:
                out.missing.discard(sid)


def export_defaults() -> None:
    """Snapshot the default sheets into assets/custom for offline installs."""
    pool: dict[str, bytes] = {}
    for s in DEFAULT_SHEETS:
        data = parse_custom_xlsx(_fetch(s.sheet_id, noop, pool), s.tab)
        save_custom(_bundled_path(s.sheet_id, s.tab), data, time.time())
        print(f"custom {sheet_key(asdict(s))}: {len(data.strings):,} strings")
