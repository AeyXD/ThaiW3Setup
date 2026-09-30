"""Problem report: content, redaction, conflicts, and upload to a local Worker (wrangler dev) when running."""
import os, sys, tempfile, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from core import report
from core.report import MAGIC, build_report, send_report

GAME = r"D:\SteamLibrary\steamapps\common\The Witcher 3"

text = build_report(GAME, "note line")
assert text.startswith(MAGIC), text[:80]
for part in ("app:", "game version:", "[install status]", "[conflicts]", "[mods]", "[mods.settings]", "note line"):
    assert part in text, part
assert str(Path.home()).lower() not in text.lower(), "home path leaked"
assert "custom_sheets" not in text

# another mod shipping tr.w3strings is reported as a conflict
game = Path(tempfile.mkdtemp())
(game / "content" / "content0").mkdir(parents=True)
(game / "bin" / "x64").mkdir(parents=True)
(game / "bin" / "x64" / "witcher3.exe").write_bytes(b"")
(game / "mods" / "modOther" / "content").mkdir(parents=True)
(game / "mods" / "modOther" / "content" / "tr.w3strings").write_bytes(b"")
(game / "mods" / "modkuntoonw3thai_1").mkdir()
from core.game_detect import identify
conflicts = report._conflicts(identify(game))
assert any("modOther has tr.w3strings" in c for c in conflicts), conflicts
assert any("modkuntoonw3thai_1" in c for c in conflicts), conflicts

os.environ["THAIW3_REPORT_URL"] = "http://127.0.0.1:8787/report"
try:
    print("uploaded", send_report(text))
except urllib.error.HTTPError as exc:
    assert exc.code == 429, exc  # local rate limit from earlier runs
    print("upload rate limited")
except urllib.error.URLError:
    print("no local worker, upload skipped")
print("test_report ok")
