"""Problem report: content, redaction, conflicts, and upload to a local Worker (wrangler dev) when running."""
import os, sys, tempfile, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME

from pathlib import Path
from core import report
from core.report import MAGIC, build_report, collect_details, compose_report, format_contact, send_report


text = build_report(GAME, "note line")
assert text.startswith(MAGIC), text[:80]
for part in ("app:", "game version:", "[install status]", "[conflicts]", "[mods]", "[mods.settings]", "note line"):
    assert part in text, part
assert str(Path.home()).lower() not in text.lower(), "home path leaked"
assert "custom_sheets" not in text
assert "\ncontact:" not in text

# contact is added after redaction, so a handle containing the Windows user name survives
import getpass
contact = format_contact("Email", f"  {getpass.getuser()}@example.com\n  ")
assert contact == f"Email: {getpass.getuser()}@example.com", contact
assert format_contact("LINE", " \n ") == ""
assert len(format_contact("other", "x" * 500)) == 200
lines = build_report(GAME, "note", contact).splitlines()
assert f"contact: {contact}" in lines[:40], lines[:6]
assert lines[2].startswith("created:") and lines[3] == f"contact: {contact}", lines[:6]

# the dialog collects details once and composes on every keystroke; same text as build_report
import time
details = collect_details(GAME)
drop_created = lambda t: [l for l in t.splitlines() if not l.startswith("created:")]
assert drop_created(compose_report(details, "note", contact)) == drop_created(build_report(GAME, "note", contact))
assert drop_created(compose_report(details)) == drop_created(build_report(GAME))
t0 = time.perf_counter()
for i in range(20):
    compose_report(details, "note " * i, contact)
per_call = (time.perf_counter() - t0) / 20
assert per_call < 0.05, f"compose_report took {per_call * 1000:.1f} ms"
print(f"compose_report {per_call * 1000:.2f} ms per call")

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
