"""Check that enabled custom sheets override the installed tr.w3strings."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME
from core.custom import DEFAULT_SHEETS, get_custom
from core.w3strings import W3Strings

out = W3Strings.load(os.path.join(GAME, "mods", "modThaiText", "content", "tr.w3strings"), "tr")
for n in map(int, sys.argv[1:]):
    sheet = DEFAULT_SHEETS[n - 1]
    strings = get_custom(sheet.sheet_id, allow_online=False, tab=sheet.tab)
    present = [sid for sid in strings if sid in out.strings]
    same = sum(1 for sid in present if out.strings[sid] == strings[sid])
    print(f"sheet {n}: {len(strings)} ids, {len(present)} exist in game, {same} applied")
