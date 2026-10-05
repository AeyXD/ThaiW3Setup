"""The update banner must link to the build for the machine it is running on."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import update
from core.update import parse_version, pick_download

WIN = {"name": "ThaiW3Setup-0.5.0.zip", "browser_download_url": "https://x/win.zip"}
MAC = {"name": "ThaiW3Setup-0.5.0-macos-arm64.zip", "browser_download_url": "https://x/mac.zip"}
TXT = {"name": "ThaiW3Setup-0.5.0.zip.sha256", "browser_download_url": "https://x/sum"}

orig = update.MACOS
try:
    for macos, both, win_only, mac_only in ((True, "https://x/mac.zip", "https://x/win.zip", "https://x/mac.zip"),
                                            (False, "https://x/win.zip", "https://x/win.zip", "https://x/mac.zip")):
        update.MACOS = macos
        assert pick_download([TXT, WIN, MAC]) == both, (macos, pick_download([TXT, WIN, MAC]))
        assert pick_download([MAC, WIN]) == both, "order in the release must not matter"
        # a release carrying only the other platform still links somewhere rather than nowhere
        assert pick_download([WIN]) == win_only, macos
        assert pick_download([MAC]) == mac_only, macos
        assert pick_download([TXT]) == "", "no zip at all"
        assert pick_download([]) == ""
finally:
    update.MACOS = orig

assert parse_version("v1.2.3") == (1, 2, 3)
assert parse_version("1.10.0") > parse_version("1.9.9")
assert parse_version("nonsense") == (0,)

print("test_update ok")
