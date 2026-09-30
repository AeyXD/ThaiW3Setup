"""Optional id-keyed "custom translation" sheets layered over the main translation (as in w3tu)."""
from __future__ import annotations

import gzip
import io
import json
import logging
import re
import time
from dataclasses import asdict, dataclass

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


# Order matters: sheets lower in the list override those above for the same id.
DEFAULT_SHEETS = [
    CustomSheet("16rgIGMmFzO1GsS-JdNXbkgTRaEma6LOuR_2EF76-TuQ", "ข้อความที่หายไป", True),
    CustomSheet("1X2VOm21x5ow_duSutaXV3AsCdz2YT1RVZZQoiPZHp14", "ชื่อเควสภาษาอังกฤษ"),
    CustomSheet("1eDp6YF3kdx9FXc8dfMFhz72QbH9wYJfKRx2gwvD4Wcg", "ปรับปรุงการแปล"),
    CustomSheet("1FDNdc-p0VJfv3ksoIAhl554jOdpecE6zw6io9tl5jPo", "สุภาพกันหน่อย"),
    CustomSheet("19uVPHxzMBwCxpnjKqakNkBqxSOm2CH173L4wpwiUjS0", "ซับนรก"),
    # "community additions": strings with no translation yet, see devtools/export_untranslated.py
    CustomSheet("1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk",
                "\u0e04\u0e33\u0e41\u0e1b\u0e25\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e40\u0e15\u0e34\u0e21\u0e08\u0e32\u0e01\u0e0a\u0e38\u0e21\u0e0a\u0e19", True),
]


def default_sheets() -> list[dict]:
    return [asdict(s) for s in DEFAULT_SHEETS]


def parse_sheet_id(text: str) -> str | None:
    text = text.strip()
    m = URL_PATTERN.search(text)
    if m:
        return m.group(1)
    return text if ID_PATTERN.match(text) else None


def sheet_url(sheet_id: str) -> str:
    return SHEET_URL.format(id=sheet_id)


def parse_custom_xlsx(data: bytes) -> tuple[str, dict[int, str]]:
    """First worksheet: a title row, a header row with ID and TRANSLATE, then data rows."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    title, id_col, tr_col = "", None, None
    out: dict[int, str] = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        cells = [_cell_text(c).strip() for c in row]
        if id_col is None:
            if i == 0 and cells:
                title = cells[0]
            upper = [c.upper() for c in cells]
            if "ID" in upper and "TRANSLATE" in upper:
                id_col, tr_col = upper.index("ID"), upper.index("TRANSLATE")
            elif i > 10:
                break
            continue
        if len(cells) <= max(id_col, tr_col):
            continue
        try:
            sid = int(float(cells[id_col]))
        except ValueError:
            continue
        if cells[tr_col]:
            out[sid] = _cell_text(row[tr_col])
    wb.close()
    if id_col is None:
        raise ValueError("ไม่พบหัวตาราง ID / TRANSLATE ในแท็บแรกของ sheet")
    return title, out


def _cache_path(sheet_id: str):
    return cache_dir() / f"custom_{sheet_id}.json.gz"


def _bundled_path(sheet_id: str):
    return assets_dir() / "custom" / f"{sheet_id}.json.gz"


def save_custom(path, title: str, strings: dict[int, str], fetched_at: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"title": title, "fetched_at": fetched_at,
                   "strings": {str(k): v for k, v in strings.items()}}, fh, ensure_ascii=False)


def load_custom(path) -> tuple[str, dict[int, str], float]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload.get("title", ""), {int(k): v for k, v in payload["strings"].items()}, float(payload["fetched_at"])


def download_custom(sheet_id: str, progress: ProgressFn = noop) -> tuple[str, dict[int, str]]:
    data = _download(EXPORT_URL.format(id=sheet_id), progress)
    title, strings = parse_custom_xlsx(data)
    save_custom(_cache_path(sheet_id), title, strings, time.time())
    return title, strings


def cached_count(sheet_id: str) -> int | None:
    for path in (_cache_path(sheet_id), _bundled_path(sheet_id)):
        if path.exists():
            try:
                return len(load_custom(path)[1])
            except (OSError, ValueError, KeyError):
                pass
    return None


def get_custom(sheet_id: str, force_download: bool = False, allow_online: bool = True,
               progress: ProgressFn = noop) -> dict[int, str]:
    cache = _cache_path(sheet_id)
    if cache.exists() and not force_download:
        try:
            _title, strings, ts = load_custom(cache)
            if time.time() - ts < CACHE_MAX_AGE or not allow_online:
                return strings
        except (OSError, ValueError, KeyError) as exc:
            log.warning("custom cache %s unreadable: %s", sheet_id, exc)
    if allow_online:
        try:
            return download_custom(sheet_id, progress)[1]
        except Exception as exc:  # network errors come in many types
            log.warning("custom sheet %s download failed: %s", sheet_id, exc)
    for path in (cache, _bundled_path(sheet_id)):
        if path.exists():
            try:
                return load_custom(path)[1]
            except (OSError, ValueError, KeyError) as exc:
                log.warning("%s unreadable: %s", path, exc)
    log.warning("custom sheet %s unavailable, skipped", sheet_id)
    return {}


def merged_overrides(sheets: list[dict], force_download: bool = False,
                     progress: ProgressFn = noop) -> dict[int, str]:
    """Merge enabled sheets top to bottom; later sheets win."""
    enabled = [s for s in sheets if s.get("enabled")]
    out: dict[int, str] = {}
    for i, s in enumerate(enabled):
        progress(i / max(1, len(enabled)), f"คำแปลเสริม: {s.get('name') or s['sheet_id']}")
        out.update(get_custom(s["sheet_id"], force_download,
                              progress=scaled(progress, i / len(enabled), (i + 1) / len(enabled))))
    progress(1.0, "โหลดคำแปลเสริมแล้ว")
    return out


def export_defaults() -> None:
    """Snapshot the default sheets into assets/custom for offline installs."""
    for s in DEFAULT_SHEETS:
        title, strings = parse_custom_xlsx(_download(EXPORT_URL.format(id=s.sheet_id), noop))
        save_custom(_bundled_path(s.sheet_id), title, strings, time.time())
        print(f"custom {s.sheet_id}: {len(strings):,} strings")
