"""Optional id-keyed "custom translation" sheets layered over the main translation (as in w3tu)."""
from __future__ import annotations

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
    # THAI column and every id listed in the tab, filled or not (empty for sheets without a THAI column)
    thai: dict[int, str] = field(default_factory=dict)
    ids: list[int] = field(default_factory=list)


@dataclass
class Overrides:
    strings: dict[int, str] = field(default_factory=dict)
    # ids shown in the game's English (name tabs switched off, or no Thai yet)
    keep_english: set[int] = field(default_factory=set)
    # ids never extended with "[English]" in two-language subtitles
    plain: set[int] = field(default_factory=set)


COMMUNITY_ID = "1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk"
UNTRANSLATED_TAB = "Untranslated"
TAB_CHARACTERS = "\u0e0a\u0e37\u0e48\u0e2d\u0e15\u0e31\u0e27\u0e25\u0e30\u0e04\u0e23"
TAB_PLACES = "\u0e0a\u0e37\u0e48\u0e2d\u0e40\u0e21\u0e37\u0e2d\u0e07"
TAB_QUESTS = "\u0e0a\u0e37\u0e48\u0e2d\u0e40\u0e04\u0e27\u0e2a"
TAB_SKILLS = "\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e01\u0e34\u0e25"
NAME_TABS = (TAB_CHARACTERS, TAB_PLACES, TAB_QUESTS, TAB_SKILLS)
NAME_GIDS = {TAB_CHARACTERS: 1219926511, TAB_PLACES: 796210995, TAB_QUESTS: 1268129566,
             TAB_SKILLS: 1710767002}
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
    *(CustomSheet(COMMUNITY_ID, name_label(tab), False, tab, NAME_GIDS.get(tab), NAME_DOUBLE) for tab in NAME_TABS),
]


def is_name_tab(sheet: dict) -> bool:
    return sheet.get("sheet_id") == COMMUNITY_ID and sheet.get("tab") in NAME_TABS


def sheet_key(sheet: dict) -> str:
    tab = sheet.get("tab") or ""
    return f"{sheet['sheet_id']}#{tab}" if tab else sheet["sheet_id"]


def default_sheets() -> list[dict]:
    return [asdict(s) for s in DEFAULT_SHEETS]


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


def parse_custom_xlsx(data: bytes, tab: str = "") -> CustomData:
    """Worksheet ``tab`` (or the first): a title row, a header row with ID and TRANSLATE (and optionally
    THAI), then data rows."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    if tab and tab not in wb.sheetnames:
        wb.close()
        raise ValueError(f"\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e41\u0e17\u0e47\u0e1a \"{tab}\" \u0e43\u0e19 sheet")
    ws = wb[tab] if tab else wb.worksheets[0]
    title, id_col, tr_col, th_col = "", None, None, None
    out = CustomData("", {})
    for i, row in enumerate(ws.iter_rows(values_only=True)):
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
        if th_col is not None:
            out.ids.extend(ids)
            if len(cells) > th_col and cells[th_col]:
                for sid in ids:
                    out.thai[sid] = cells[th_col]
        if len(cells) > tr_col and cells[tr_col]:
            for sid in ids:
                out.strings[sid] = _cell_text(row[tr_col])
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


def save_custom(path, data: CustomData, fetched_at: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"title": data.title, "fetched_at": fetched_at,
                   "strings": {str(k): v for k, v in data.strings.items()},
                   "thai": {str(k): v for k, v in data.thai.items()},
                   "ids": data.ids}, fh, ensure_ascii=False)


def load_custom(path) -> tuple[CustomData, float, bool]:
    """The flag is False for files written before THAI and ids were saved."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    data = CustomData(payload.get("title", ""), {int(k): v for k, v in payload["strings"].items()},
                      {int(k): v for k, v in payload.get("thai", {}).items()},
                      [int(k) for k in payload.get("ids", [])])
    return data, float(payload["fetched_at"]), "ids" in payload


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


def cached_count(sheet_id: str, tab: str = "") -> int | None:
    for path in (_cache_path(sheet_id, tab), _bundled_path(sheet_id, tab)):
        if path.exists():
            try:
                return len(load_custom(path)[0].strings)
            except (OSError, ValueError, KeyError):
                pass
    return None


def get_custom_data(sheet_id: str, force_download: bool = False, allow_online: bool = True,
                    progress: ProgressFn = noop, tab: str = "",
                    pool: dict[str, bytes] | None = None) -> CustomData:
    cache = _cache_path(sheet_id, tab)
    name_tab = is_name_tab({"sheet_id": sheet_id, "tab": tab})
    if cache.exists() and not force_download:
        try:
            data, ts, complete = load_custom(cache)
            fresh = time.time() - ts < CACHE_MAX_AGE and (complete or not name_tab)
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
    progress(1.0, "โหลดคำแปลเสริมแล้ว")
    return out


def _apply_name_tab(out: Overrides, data: CustomData, mode: str) -> None:
    """mode is NAME_THAI or NAME_DOUBLE for a switched-on tab, empty for a switched-off one."""
    shown = data.thai if mode == NAME_THAI else data.strings if mode == NAME_DOUBLE else {}
    for sid in set(data.ids) | set(data.strings) | set(data.thai):
        out.plain.add(sid)
        if shown.get(sid):
            out.strings[sid] = shown[sid]
            out.keep_english.discard(sid)
        else:
            out.strings.pop(sid, None)
            out.keep_english.add(sid)


def export_defaults() -> None:
    """Snapshot the default sheets into assets/custom for offline installs."""
    pool: dict[str, bytes] = {}
    for s in DEFAULT_SHEETS:
        data = parse_custom_xlsx(_fetch(s.sheet_id, noop, pool), s.tab)
        save_custom(_bundled_path(s.sheet_id, s.tab), data, time.time())
        print(f"custom {sheet_key(asdict(s))}: {len(data.strings):,} strings")
