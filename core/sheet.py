"""Download the community Thai translation (w3tu Google Sheets) and cache it."""
from __future__ import annotations

import gzip
import io
import json
import logging
import time
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .paths import assets_dir, cache_dir
from .progress import ProgressFn, noop, scaled

log = logging.getLogger(__name__)

EXPORT_URL = "https://docs.google.com/spreadsheets/d/{id}/export?format=xlsx"

# w3tu sheets keyed by string id (column A id, column E Thai).
# Later sources override earlier ones for the same string id.
SOURCES = [
    ("1lwoUZkMQcFwl_nlzV7UG9qxij6CMc5YuJOSsMuK3ZH8", ["v3", "v4"]),
    ("1YZvH6sd3XjPcLmz5nlRVkHd2Wm1psU1KthHtwSeG3t4", ["NextGen"]),
]
# Community sheet keyed by English text (column A English, column C Thai), all tabs
# after the guidelines tab. Only used for ids the w3tu sheets do not translate.
TEXT_SOURCES = [
    "1Ar5MVSc4Mdr7YAFssOmTJcJ9IyHrtxUZxt649-DhnA4",
]

CACHE_NAME = "translations.json.gz"
CACHE_FORMAT = 2
CACHE_MAX_AGE = 24 * 3600
USER_AGENT = "ThaiW3Setup (+https://github.com/)"


@dataclass
class Translations:
    thai: dict[int, str]
    by_text: dict[str, str]  # normalized English text -> Thai
    source: str
    fetched_at: float

    @property
    def age_text(self) -> str:
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(self.fetched_at))


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def parse_xlsx(data: bytes, sheets: list[str]) -> dict[int, str]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out: dict[int, str] = {}
    for name in sheets:
        if name not in wb.sheetnames:
            log.warning("sheet %s not found", name)
            continue
        for row in wb[name].iter_rows(min_row=3, max_col=5, values_only=True):
            if not row or row[0] is None or len(row) < 5:
                continue
            try:
                sid = int(str(row[0]).strip())
            except ValueError:
                continue
            thai = _cell_text(row[4])
            if thai.strip():
                out[sid] = thai
    wb.close()
    return out


def normalize(text: str) -> str:
    return " ".join(text.split())


def parse_text_xlsx(data: bytes) -> dict[str, str]:
    """English -> Thai; when one English line has several translations the most common wins."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    votes: dict[str, Counter] = {}
    for ws in wb.worksheets[1:]:
        for row in ws.iter_rows(min_row=5, max_col=3, values_only=True):
            if not row or len(row) < 3 or row[0] is None or row[2] is None:
                continue
            english, thai = normalize(_cell_text(row[0])), _cell_text(row[2]).strip()
            if english and thai:
                votes.setdefault(english, Counter())[thai] += 1
    wb.close()
    return {en: c.most_common(1)[0][0] for en, c in votes.items()}


def _download(url: str, progress: ProgressFn) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        buf = bytearray()
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            buf += chunk
            if total:
                progress(len(buf) / total, f"กำลังดาวน์โหลดคำแปล {len(buf) // 1024:,} KB")
            else:
                progress(0.5, f"กำลังดาวน์โหลดคำแปล {len(buf) // 1024:,} KB")
    return bytes(buf)


def fetch_online(progress: ProgressFn = noop) -> tuple[dict[int, str], dict[str, str]]:
    jobs = [(sheet_id, tabs) for sheet_id, tabs in SOURCES] + [(sheet_id, None) for sheet_id in TEXT_SOURCES]
    merged: dict[int, str] = {}
    by_text: dict[str, str] = {}
    step = 1.0 / len(jobs)
    for i, (sheet_id, tabs) in enumerate(jobs):
        p = scaled(progress, i * step, (i + 0.7) * step)
        data = _download(EXPORT_URL.format(id=sheet_id), p)
        progress((i + 0.75) * step, "กำลังอ่านไฟล์คำแปล...")
        if tabs is None:
            by_text.update(parse_text_xlsx(data))
        else:
            merged.update(parse_xlsx(data, tabs))
    return merged, by_text


def save_json(path: Path, thai: dict[int, str], by_text: dict[str, str], fetched_at: float) -> None:
    payload = {"format": CACHE_FORMAT, "fetched_at": fetched_at,
               "strings": {str(k): v for k, v in thai.items()}, "text": by_text}
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def load_json(path: Path) -> tuple[dict[int, str], dict[str, str], float]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("format") != CACHE_FORMAT:
        raise ValueError(f"old cache format in {path}")
    return ({int(k): v for k, v in payload["strings"].items()}, payload["text"],
            float(payload.get("fetched_at", 0)))


def get_translations(force_download: bool = False, allow_online: bool = True,
                     progress: ProgressFn = noop) -> Translations:
    cache = cache_dir() / CACHE_NAME
    if cache.exists() and not force_download:
        try:
            thai, by_text, ts = load_json(cache)
            if time.time() - ts < CACHE_MAX_AGE or not allow_online:
                return Translations(thai, by_text, "คำแปลที่เก็บไว้ในเครื่อง", ts)
        except (OSError, ValueError, KeyError) as exc:
            log.warning("cache unreadable: %s", exc)

    if allow_online:
        try:
            thai, by_text = fetch_online(progress)
            ts = time.time()
            save_json(cache, thai, by_text, ts)
            return Translations(thai, by_text, "Google Sheet (ล่าสุด)", ts)
        except Exception as exc:  # network errors come in many types
            log.warning("online download failed: %s", exc)

    for path, label in ((cache, "คำแปลในเครื่อง (ออฟไลน์)"), (assets_dir() / CACHE_NAME, "คำแปลที่มากับโปรแกรม (ออฟไลน์)")):
        if path.exists():
            try:
                thai, by_text, ts = load_json(path)
                return Translations(thai, by_text, label, ts)
            except (OSError, ValueError, KeyError) as exc:
                log.warning("%s unreadable: %s", path, exc)
    raise RuntimeError("ดาวน์โหลดคำแปลไม่สำเร็จ และไม่พบคำแปลสำรองในโปรแกรม")


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Download translations and write a gzip JSON snapshot")
    ap.add_argument("--export", type=Path, default=assets_dir() / CACHE_NAME)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    data, by_text = fetch_online(lambda f, m: print(f"\r{f * 100:5.1f}% {m}", end="", file=sys.stderr))
    args.export.parent.mkdir(parents=True, exist_ok=True)
    save_json(args.export, data, by_text, time.time())
    print(f"\nwrote {len(data):,} id strings and {len(by_text):,} text strings to {args.export}")
    from .custom import export_defaults
    export_defaults()
