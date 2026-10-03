"""export() builds the same mod folders as install() outside the game; copied into mods they read as installed."""
import json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME, game_path

from pathlib import Path
from core.game_detect import GameInfo, identify
from core.installer import EXPORT_DIR, EXPORT_README, MANIFEST, MOD_TEXT, _sha1, export, status
from core.options import load_options


opts = load_options()
opts.game_path = GAME
out = Path(tempfile.mkdtemp())
report = export(opts, out)
target = out / EXPORT_DIR
assert report.output == str(target), report.output
assert sorted(p.name for p in target.iterdir() if p.is_dir()) == sorted(report.mods), list(target.iterdir())
assert "mods" in (target / EXPORT_README).read_text(encoding="utf-8-sig")

manifest = json.loads((target / MOD_TEXT / MANIFEST).read_text(encoding="utf-8"))
for rel, digest in manifest["files"].items():
    assert _sha1(target / rel) == digest, rel

# the user copies the folders into the game's mods folder by hand
fake = Path(tempfile.mkdtemp())
for name in report.mods:
    shutil.copytree(target / name, fake / "mods" / name)
st = status(GameInfo(fake, identify(GAME).edition))
assert st.installed and st.version == manifest["version"] and not st.modified, st

# a second export replaces our folders instead of failing on copytree
export(opts, out)
print("test_export ok", report.mods, f"{report.percent:.2f}%")
