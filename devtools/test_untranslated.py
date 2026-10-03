import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME

tmp = tempfile.mkdtemp()
os.environ["THAIW3SETUP_DATA"] = tmp  # keep the settings test away from the real profile

from core import custom
from core.custom import merged_overrides, default_sheets, parse_custom_xlsx
from core.game_detect import identify
from core.options import InstallOptions, load_options, settings_path
from core.sheet import get_translations
from core.text_builder import build_texts, untranslated
from export_untranslated import build_rows, write_xlsx


# build_rows keeps translated/annotated rows, drops stale empty ones, adds new ids
rows = build_rows({1: "new", 3: "still missing"},
                  {2: ["done", "\u0e41\u0e1b\u0e25\u0e41\u0e25\u0e49\u0e27", ""], 3: ["old text", "", ""],
                   4: ["stale", "", ""], 5: ["noted", "", "check context"]})
assert rows == [[1, "new", "", ""], [2, "done", "\u0e41\u0e1b\u0e25\u0e41\u0e25\u0e49\u0e27", ""],
                [3, "still missing", "", ""], [5, "noted", "", "check context"]], rows

# xlsx written by the exporter is readable as a custom sheet
path = os.path.join(tmp, "u.xlsx")
write_xlsx(path, rows)
data = parse_custom_xlsx(open(path, "rb").read())
title, strings = data.title, data.strings
assert title.startswith("ThaiW3Setup") and strings == {2: "\u0e41\u0e1b\u0e25\u0e41\u0e25\u0e49\u0e27"}, strings

# untranslated() agrees with build_texts
g = identify(GAME)
tr = get_translations(allow_online=False)
ov = merged_overrides(default_sheets(), progress=lambda f, m: None)
pending = untranslated(g, tr.thai, tr.by_text, ov)
res = build_texts(g, tr.thai, InstallOptions(GAME), by_text=tr.by_text, overrides=ov)
assert len(pending) == res.total - res.translated - 1, (len(pending), res.total, res.translated)  # 1 empty string
print("untranslated", len(pending))

# settings saved before a default sheet existed pick it up once, and keep it removed afterwards
new = custom.CustomSheet("1" + "N" * 40, "new default", True)
custom.DEFAULT_SHEETS.append(new)
old = [s for s in default_sheets() if s["sheet_id"] != new.sheet_id]
settings_path().write_text(json.dumps({"custom_sheets": old}), encoding="utf-8")
opts = load_options()
assert [s["sheet_id"] for s in opts.custom_sheets][-1] == new.sheet_id
opts.custom_sheets.pop()
settings_path().write_text(json.dumps({"custom_sheets": opts.custom_sheets,
                                       "known_default_sheets": opts.known_default_sheets}), encoding="utf-8")
assert new.sheet_id not in [s["sheet_id"] for s in load_options().custom_sheets]
custom.DEFAULT_SHEETS.remove(new)
print("test_untranslated ok")
