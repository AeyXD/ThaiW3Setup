"""Check that enabled custom sheets override the installed tr.w3strings."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME
from core.custom import DEFAULT_SHEETS, default_sheets, get_custom, hidden_sheets, sheet_key
from core.options import InstallOptions, _add_new_default_sheets
from core.w3strings import W3Strings
from devtools.import_en_csv import build_rows, parse_csv

csv = (";meta[language=en]\n; id      |key(hex)|key(str)| text\n"
       "1000008|||A few.\n1434120|1B251AA3||Line one\nline two\n2000|||a | b\n")
assert parse_csv(csv) == {1000008: "A few.", 1434120: "Line one\nline two", 2000: "a | b"}
assert build_rows({1: "new", 2: "two"}, {1: ["old", "th", ""], 3: ["gone", "", ""], 4: ["x", "", "note"]}) == [
    [1, "new", "th", ""], [2, "two", "", ""], [4, "x", "", "note"]]

hidden = {sheet_key(s) for s in hidden_sheets()}
assert hidden and not hidden & {sheet_key(s) for s in default_sheets()}
opts = InstallOptions(custom_sheets=[], known_default_sheets=[])
_add_new_default_sheets(opts)
assert opts.custom_sheets and not hidden & {sheet_key(s) for s in opts.custom_sheets}

out = W3Strings.load(os.path.join(GAME, "mods", "modThaiText", "content", "tr.w3strings"), "tr")
for n in map(int, sys.argv[1:]):
    sheet = DEFAULT_SHEETS[n - 1]
    strings = get_custom(sheet.sheet_id, allow_online=False, tab=sheet.tab)
    present = [sid for sid in strings if sid in out.strings]
    same = sum(1 for sid in present if out.strings[sid] == strings[sid])
    print(f"sheet {n}: {len(strings)} ids, {len(present)} exist in game, {same} applied")
