"""The update banner must link to the build for the machine it is running on."""
import io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import update
from core.update import RELEASES_URL, parse_version, pick_download

WIN = {"name": "ThaiW3Setup-0.5.0.zip", "browser_download_url": "https://x/win.zip"}
MAC = {"name": "ThaiW3Setup-0.5.0-macos-arm64.zip", "browser_download_url": "https://x/mac.zip"}
TXT = {"name": "ThaiW3Setup-0.5.0.zip.sha256", "browser_download_url": "https://x/sum"}


def fake_release(assets):
    body = {"tag_name": "v9.9.9", "body": "notes", "html_url": "https://x/tag/v9.9.9", "assets": assets}
    return lambda req, timeout: io.BytesIO(json.dumps(body).encode())


orig = update.MACOS, update.urllib.request.urlopen
try:
    for macos, ours, other in ((True, MAC, WIN), (False, WIN, MAC)):
        update.MACOS = macos
        url = ours["browser_download_url"]
        assert pick_download([TXT, WIN, MAC]) == url, (macos, pick_download([TXT, WIN, MAC]))
        assert pick_download([MAC, WIN]) == url, "order in the release must not matter"
        assert pick_download([ours]) == url
        # the other platform's zip is never offered: a Mac user would download the Windows .exe
        # (regular releases carry only the Windows zip, the macOS build is a separate pre-release)
        assert pick_download([other]) == "", macos
        assert pick_download([TXT]) == "", "no zip at all"
        assert pick_download([]) == ""

        update.urllib.request.urlopen = fake_release([TXT, other])
        info = update.fetch_latest()
        assert info.download_url == RELEASES_URL, (macos, info.download_url)
        assert info.page_url == "https://x/tag/v9.9.9" and info.version == "9.9.9"
        update.urllib.request.urlopen = fake_release([other, ours])
        assert update.fetch_latest().download_url == url, macos
finally:
    update.MACOS, update.urllib.request.urlopen = orig

assert parse_version("v1.2.3") == (1, 2, 3)
assert parse_version("1.10.0") > parse_version("1.9.9")
assert parse_version("nonsense") == (0,)

print("test_update ok")
