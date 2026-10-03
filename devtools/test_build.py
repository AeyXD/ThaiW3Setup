import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME
from core.game_detect import identify
from core.options import InstallOptions, MODE_DOUBLE, MODE_THAI
from core.sheet import get_translations
from core.text_builder import build_texts, LANGUAGE_NAME_ID
from core.w3strings import W3Strings

g = identify(GAME)
print("edition", g.edition, g.supported, len(g.strings_files("en")), "en files")
t0 = time.time()
tr = get_translations(progress=lambda f, m: None)
print("translations", len(tr.thai), tr.source, round(time.time() - t0, 1), "s")
for mode, slot in ((MODE_THAI, "tr"), (MODE_DOUBLE, "tr"), (MODE_THAI, "en")):
    t0 = time.time()
    res = build_texts(g, tr.thai, InstallOptions(GAME, mode=mode, slot=slot), by_text=tr.by_text)
    print(mode, slot, {k: len(v) for k, v in res.files.items()}, f"{res.percent:.2f}%", round(time.time() - t0, 1), "s")
    w = W3Strings.parse(res.files[f"{slot}.w3strings"], slot)
    print("  version", w.version, "strings", len(w.strings), "keys", len(w.keys))
    print("  label", ascii(w.strings.get(LANGUAGE_NAME_ID)))
    sample = [s for s in w.strings.values() if "  [" in s][:1]
    print("  double sample", ascii(sample[0][:80]) if sample else None)
    if "en.w3strings" in res.files and slot == "tr":
        lab = W3Strings.parse(res.files["en.w3strings"], "en")
        print("  en label file", len(lab.strings), ascii(lab.strings.get(LANGUAGE_NAME_ID)))
