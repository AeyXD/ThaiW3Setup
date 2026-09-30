"""Publish proper names (characters, places, quests, skills) as tabs of the community sheet.

Each tab uses the custom-sheet layout plus a THAI column: people type the Thai name there
and TRANSLATE becomes "English (Thai)" by formula, so enabling the tab in ThaiW3Setup
shows e.g. "Yennefer (Thai)". One row covers every string id of a name (comma separated).
Re-running keeps what people typed, also for rows someone moved to another tab.

Candidates are strings the translation keeps in English and that look like names; the
split between characters and places is a guess (string keys, place words, Thai place
prefixes) and meant to be fixed by hand. Skills come from their string keys (skill_name_*).
Setup: see export_untranslated.py.

    python devtools/export_names.py                       # refresh the tabs of the community sheet
    python devtools/export_names.py --no-upload --xlsx names.xlsx
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.custom import (COMMUNITY_ID, NAME_TABS, TAB_CHARACTERS, TAB_PLACES, TAB_QUESTS, TAB_SKILLS,
                         get_custom)
from core.game_detect import identify
from core.options import load_options
from core.sheet import get_translations
from core.text_builder import _load_merged, _thai_for
from core.w3strings import hash_key
from export_untranslated import _client

QUEST_SHEET = "1X2VOm21x5ow_duSutaXV3AsCdz2YT1RVZZQoiPZHp14"
HEADER = ["ID", "ENGLISH", "THAI", "TRANSLATE", "NOTE"]
COLUMN_WIDTHS = [150, 300, 240, 360, 220]
UPDATED_TH = "\u0e2d\u0e31\u0e1b\u0e40\u0e14\u0e15"  # "updated"

PARTICLES = {"of", "the", "van", "de", "var", "aep", "von", "an", "la", "le", "du", "der", "and", "in", "on", "at"}
WORD = re.compile(r"^[A-Z][A-Za-z'\-.]*$")
PLACE_WORDS = {
    "village", "camp", "cave", "caves", "bridge", "inn", "estate", "castle", "palace", "harbor", "harbour",
    "crossroads", "mill", "farm", "farmstead", "tower", "ruins", "cemetery", "port", "gate", "square",
    "isle", "island", "islands", "fort", "fortress", "keep", "swamp", "forest", "woods", "lake", "grove",
    "hill", "hills", "mountain", "mountains", "pass", "road", "tavern", "vineyard", "bay", "bog", "marsh",
    "mine", "mines", "quarry", "outpost", "hut", "lighthouse", "temple", "sanctuary", "monastery",
    "district", "quarter", "garden", "gardens", "prison", "estate", "manor", "abbey", "shrine", "valley",
    "coast", "beach", "field", "fields", "meadow", "clearing", "dock", "docks", "wharf", "sewers", "well",
}
REGIONS = {"Velen", "Novigrad", "Oxenfurt", "Skellige", "Toussaint", "Beauclair", "Vizima", "Kaer Morhen",
           "White Orchard", "Nilfgaard", "Temeria", "Redania", "Kaedwen", "Aedirn", "Cintra", "Brokilon",
           "Ard Skellig", "Undvik", "An Skellig", "Spikeroog", "Faroe", "Hindarsfjall", "Kaer Trolde"}
# items, skills and alchemy that carry a proper noun ("Nilfgaardian Armor Set", "Glyph of Quen")
ITEM_WORDS = {
    "potion", "armor", "armour", "set", "glyph", "rune", "enhanced", "superior", "mastercrafted", "boosts",
    "intensity", "sword", "oil", "decoction", "mutagen", "trousers", "gauntlets", "boots", "blade", "bomb",
    "recipe", "diagram", "formula", "upgrade", "gear", "crossbow", "bolt", "bolts", "dust", "extract",
    "puffball", "essence", "saddle", "saddlebags", "blinders", "card", "cards", "location", "skill", "sign",
}
THAI_CHAR = re.compile("[\u0e00-\u0e7f]")
# the translation writes some places as "<Thai word> English", e.g. "city Novigrad"
THAI_PLACE_PREFIXES = {
    "\u0e40\u0e21\u0e37\u0e2d\u0e07", "\u0e14\u0e34\u0e19\u0e41\u0e14\u0e19",
    "\u0e2b\u0e21\u0e39\u0e48\u0e1a\u0e49\u0e32\u0e19", "\u0e40\u0e01\u0e32\u0e30",
    "\u0e1b\u0e23\u0e32\u0e2a\u0e32\u0e17", "\u0e16\u0e49\u0e33", "\u0e1b\u0e49\u0e2d\u0e21",
}


def _title(tab: str) -> str:
    return f"ThaiW3Setup - {tab} ({UPDATED_TH} {time.strftime('%d/%m/%Y')})"


def looks_like_name(text: str) -> bool:
    words = text.split()
    if not 1 <= len(words) <= 4 or text.isupper() or text.endswith("-"):
        return False
    if any(re.search(r"[a-z][A-Z]|^[A-Z]{2}", w) for w in words):  # VSync, UI labels
        return False
    return bool(WORD.match(words[0])) and all(WORD.match(w) or w in PARTICLES for w in words)


def _slugs(name: str) -> set[str]:
    low = name.lower()
    plain = re.sub(r"[^a-z0-9 ]", "", low)
    return {low, low.replace(" ", "_"), low.replace(" ", ""), plain.replace(" ", "_"), plain.replace(" ", "")}


def _core_words(name: str) -> list[str]:
    parts = (p for w in name.split() if w not in PARTICLES for p in w.split("-"))
    return [p.strip("'.").lower() for p in parts if p.strip("'.")]


def lowercase_words(texts) -> set[str]:
    """Words used in lower case somewhere in the game text, i.e. ordinary words, not names."""
    out: set[str] = set()
    for t in texts:
        out.update(w.strip("'") for w in re.findall(r"[a-z][a-z']*", t))
    return out


def classify(name: str, keys: set[int], thai_place: bool, lower: set[str]) -> str | None:
    slugs = _slugs(name)
    if any(w in ITEM_WORDS for w in _core_words(name)):
        return None
    if (thai_place or name in REGIONS or any(hash_key("map_location_" + s) in keys for s in slugs)
            or name.split()[-1].lower() in PLACE_WORDS):
        return TAB_PLACES
    if any(hash_key(s) in keys for s in slugs):
        return TAB_CHARACTERS
    if any(w not in lower for w in _core_words(name)):
        return TAB_CHARACTERS
    return None


def skill_keys() -> list[str]:
    """String keys of the character skill tree, perks and mutations (not the basic attacks)."""
    keys = [f"skill_name_{tree}_s{n}" for tree in ("sword", "magic", "alchemy") for n in range(1, 31)]
    keys += [f"skill_name_perk_{n}" for n in range(1, 31)]
    keys += [f"skill_name_mutation_{n}" for n in range(1, 21)]
    return keys


def collect(english, thai: dict[int, str], by_text: dict[str, str] | None,
            quests: dict[int, str]) -> tuple[dict[str, dict[str, list[int]]], dict[str, str]]:
    """tab -> English name -> string ids, and English quest name -> current Thai (prefill)."""
    tabs: dict[str, dict[str, list[int]]] = {t: {} for t in NAME_TABS}
    prefill: dict[str, str] = {}
    for sid in sorted(quests):
        name = english.strings.get(sid, "").strip()
        if not name or len(name) > 80 or "<" in name:
            continue
        tabs[TAB_QUESTS].setdefault(name, []).append(sid)
        th = (_thai_for(sid, name, thai, by_text, {}) or "").strip()
        if THAI_CHAR.search(th):
            prefill.setdefault(name, th)

    by_key = {k: sid for sid, k in english.keys.items()}
    skill_ids = [by_key[hash_key(k)] for k in skill_keys() if hash_key(k) in by_key]
    skill_names = {english.strings[sid].strip() for sid in skill_ids} - set(tabs[TAB_QUESTS]) - {""}
    for sid in skill_ids:
        th = (_thai_for(sid, english.strings[sid], thai, by_text, {}) or "").strip()
        if THAI_CHAR.search(th):
            prefill.setdefault(english.strings[sid].strip(), th)

    found: dict[str, list[int]] = {}
    thai_place: set[str] = set()
    for sid, text in english.strings.items():
        name = text.strip()
        if name in skill_names:
            tabs[TAB_SKILLS].setdefault(name, []).append(sid)
            continue
        if name in tabs[TAB_QUESTS] or not looks_like_name(name):
            continue
        th = (_thai_for(sid, name, thai, by_text, {}) or "").strip()
        if th == name:
            found.setdefault(name, []).append(sid)
        elif th.endswith(" " + name) and th[:-len(name)].strip() in THAI_PLACE_PREFIXES:
            found.setdefault(name, []).append(sid)
            thai_place.add(name)

    lower = lowercase_words(english.strings.values())
    for name, ids in found.items():
        keys = {english.keys[i] for i in ids if i in english.keys}
        tab = classify(name, keys, name in thai_place, lower)
        if tab:
            tabs[tab][name] = sorted(ids)
    for name in tabs[TAB_SKILLS]:
        tabs[TAB_SKILLS][name].sort()
    return tabs, prefill


def _existing(ws) -> dict[str, list]:
    """English -> [ids, thai, note] from a tab in our layout."""
    values = ws.get_all_values()
    header = next((i for i, row in enumerate(values[:10]) if "ENGLISH" in row and "THAI" in row), None)
    if header is None:
        return {}
    cols = {h: values[header].index(h) for h in HEADER if h in values[header]}
    out = {}
    for row in values[header + 1:]:
        cell = lambda h: row[cols[h]].strip() if h in cols and cols[h] < len(row) else ""
        if cell("ENGLISH"):
            ids = [int(float(p)) for p in cell("ID").split(",") if p.strip().replace(".", "", 1).isdigit()]
            out[cell("ENGLISH")] = [ids, cell("THAI"), cell("NOTE")]
    return out


def build_tabs(found: dict[str, dict[str, list[int]]], prefill: dict[str, str],
               existing: dict[str, dict[str, list]]) -> dict[str, list[list]]:
    """Rows [ids, english, thai, note] per tab. A name stays in the tab where it already is,
    except skills, which are known exactly from their string keys; rows people filled in are
    kept even when the name is no longer found."""
    placed = {name: tab for tab in NAME_TABS for name in existing.get(tab, {})}
    rows: dict[str, dict[str, list]] = {t: {} for t in NAME_TABS}
    done: set[str] = set()
    for tab in NAME_TABS:
        for name, ids in found.get(tab, {}).items():
            home = tab if tab == TAB_SKILLS else placed.get(name, tab)
            old = existing.get(placed.get(name, ""), {}).get(name)
            thai, note = (old[1], old[2]) if old else (prefill.get(name, ""), "")
            rows[home][name] = [ids, name, thai, note]
            done.add(name)
    for tab in NAME_TABS:
        for name, (ids, thai, note) in existing.get(tab, {}).items():
            if name not in done and (thai or note) and ids:
                rows[tab][name] = [ids, name, thai, note]
    return {tab: [rows[tab][n] for n in sorted(rows[tab], key=str.lower)] for tab in NAME_TABS}


def _id_cell(ids: list[int]):
    return ids[0] if len(ids) == 1 else ", ".join(map(str, ids))


def _formula(r: int) -> str:
    return f'=IF(C{r}="","",B{r}&" ("&C{r}&")")'


def write_xlsx(path: str, tabs: dict[str, list[list]]) -> None:
    import openpyxl
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for tab, rows in tabs.items():
        ws = wb.create_sheet(tab)
        ws.append([_title(tab)])
        ws.append(HEADER)
        for r, (ids, name, thai, note) in enumerate(rows, 3):
            ws.append([_id_cell(ids), name, thai, _formula(r), note])
        for cell in ws[2]:
            cell.font = Font(bold=True)
        for col, width in zip("ABCDE", COLUMN_WIDTHS):
            ws.column_dimensions[col].width = width / 7
        ws.freeze_panes = "A3"
    wb.save(path)


def _format(sh, ws, rows: int) -> None:
    sid = ws.id
    requests = [
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
                                   "fields": "gridProperties.frozenRowCount"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 2, "endRowIndex": rows + 2,
                                  "startColumnIndex": 0, "endColumnIndex": 5},
                        "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                        "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment"}},
    ]
    for i, width in enumerate(COLUMN_WIDTHS):
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": width}, "fields": "pixelSize"}})
    meta = sh.fetch_sheet_metadata({"fields": "sheets(properties.sheetId,protectedRanges)"})
    protected = any(s.get("protectedRanges") for s in meta["sheets"] if s["properties"]["sheetId"] == sid)
    if not protected:
        # "type the Thai name in the THAI column only"
        note = ("\u0e43\u0e2a\u0e48\u0e0a\u0e37\u0e48\u0e2d\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22"
                "\u0e43\u0e19\u0e04\u0e2d\u0e25\u0e31\u0e21\u0e19\u0e4c THAI \u0e40\u0e17\u0e48\u0e32\u0e19\u0e31\u0e49\u0e19")
        for start, end in ((0, 2), (3, 4)):
            requests.append({"addProtectedRange": {"protectedRange": {
                "range": {"sheetId": sid, "startColumnIndex": start, "endColumnIndex": end},
                "description": note, "warningOnly": True}}})
    sh.batch_update({"requests": requests})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game", default=None, help="game folder (default: the one saved in settings)")
    ap.add_argument("--sheet", default=COMMUNITY_ID, help="sheet id to write the tabs to")
    ap.add_argument("--xlsx", help="also save the tabs to this .xlsx file")
    ap.add_argument("--no-upload", action="store_true", help="skip Google Sheets (use with --xlsx)")
    args = ap.parse_args()

    game = identify(args.game or load_options().game_path)
    if not game.supported:
        sys.exit(f"unsupported game folder: {game.label}")
    english = _load_merged(game, "en", [])
    tr = get_translations()
    found, prefill = collect(english, tr.thai, tr.by_text, get_custom(QUEST_SHEET))

    sh = None
    sheets = {}
    existing: dict[str, dict[str, list]] = {}
    if not args.no_upload:
        sh = _client().open_by_key(args.sheet)
        sheets = {w.title: w for w in sh.worksheets()}
        existing = {tab: _existing(sheets[tab]) for tab in NAME_TABS if tab in sheets}

    tabs = build_tabs(found, prefill, existing)
    for tab, rows in tabs.items():
        filled = sum(1 for r in rows if r[2])
        print(f"{ascii(tab)}: {len(rows):,} names ({filled:,} with Thai)")
    if args.xlsx:
        write_xlsx(args.xlsx, tabs)
        print(f"wrote {args.xlsx}")
    if sh is None:
        return

    for tab, rows in tabs.items():
        ws = sheets.get(tab) or sh.add_worksheet(tab, rows=len(rows) + 2, cols=len(HEADER))
        ws.clear()
        if ws.row_count < len(rows) + 2 or ws.col_count < len(HEADER):
            ws.resize(rows=max(ws.row_count, len(rows) + 2), cols=max(ws.col_count, len(HEADER)))
        values = [[_title(tab)], HEADER] + [[_id_cell(ids), name, thai, "", note] for ids, name, thai, note in rows]
        ws.update(values, "A1", value_input_option="RAW")
        if rows:
            ws.update([[_formula(r)] for r in range(3, len(rows) + 3)], f"D3:D{len(rows) + 2}",
                      value_input_option="USER_ENTERED")
        _format(sh, ws, len(rows))
        print(f"{ascii(tab)} gid={ws.id}")
    print(sh.url)


if __name__ == "__main__":
    main()
