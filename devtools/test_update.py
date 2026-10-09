"""The update banner must link to the build for the machine it is running on."""
import io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import update
from core.update import RELEASES_URL, check_for_update, parse_version, pick_download

WIN = {"name": "ThaiW3Setup-0.5.0.zip", "browser_download_url": "https://x/win.zip"}
MAC = {"name": "ThaiW3Setup-macos-arm64-0.5.0.zip", "browser_download_url": "https://x/mac.zip"}
TXT = {"name": "ThaiW3Setup-0.5.0.zip.sha256", "browser_download_url": "https://x/sum"}


def release(version, assets, prerelease=False, draft=False):
    return {"tag_name": f"v{version}", "body": "notes", "html_url": f"https://x/tag/v{version}",
            "assets": assets, "prerelease": prerelease, "draft": draft}


def serve(*releases):
    """GitHub as the client sees it: /releases/latest is the newest non-pre-release, /releases all of them."""
    def urlopen(req, timeout, context=None):
        if req.full_url == update.LATEST_URL:
            body = next(r for r in releases if not r["prerelease"] and not r["draft"])
        else:
            assert req.full_url == update.RELEASES_API, req.full_url
            body = list(releases)
        return io.BytesIO(json.dumps(body).encode())
    update.urllib.request.urlopen = urlopen


orig = update.MACOS, update.urllib.request.urlopen
try:
    for macos, ours, other in ((True, MAC, WIN), (False, WIN, MAC)):
        update.MACOS = macos
        url = ours["browser_download_url"]
        assert pick_download([TXT, WIN, MAC]) == url, (macos, pick_download([TXT, WIN, MAC]))
        assert pick_download([MAC, WIN]) == url, "order in the release must not matter"
        assert pick_download([ours]) == url
        # the other platform's zip is never offered: a Mac user would download the Windows .exe
        assert pick_download([other]) == "", macos
        assert pick_download([TXT]) == "", "no zip at all"
        assert pick_download([]) == ""

        # one release carrying both platforms' zips
        serve(release("9.9.9", [TXT, other, ours]))
        info = update.fetch_latest()
        assert info.download_url == url, (macos, info.download_url)
        assert info.page_url == "https://x/tag/v9.9.9" and info.version == "9.9.9"

    # Windows reads /releases/latest only, falling back to the list when its zip is missing
    update.MACOS = False
    serve(release("9.9.9", [TXT, MAC]))
    assert update.fetch_latest().download_url == RELEASES_URL
    serve(release("9.9.10", [MAC], prerelease=True), release("9.9.9", [WIN]))
    assert update.fetch_latest().version == "9.9.9", "a pre-release is not offered on Windows"

    # macOS skips a release whose macOS build failed, and counts pre-releases
    update.MACOS = True
    serve(release("9.9.10", [WIN]), release("9.9.9", [WIN, MAC]))
    info = update.fetch_latest()
    assert (info.version, info.download_url) == ("9.9.9", "https://x/mac.zip"), info
    serve(release("9.9.10", [MAC], prerelease=True), release("9.9.9", [WIN, MAC]))
    assert update.fetch_latest().version == "9.9.10"
    serve(release("9.9.11", [MAC], draft=True), release("9.9.9", [MAC]))
    assert update.fetch_latest().version == "9.9.9", "drafts are skipped"
    # no release with a macOS build at all: nothing to offer rather than a Windows zip
    serve(release("9.9.9", [WIN, TXT]))
    assert update.fetch_latest() is None
    assert check_for_update() is None
    serve(release("0.0.1", [MAC]))
    assert check_for_update() is None, "older than this build"
finally:
    update.MACOS, update.urllib.request.urlopen = orig

# GitHub lists assets by name and setups before 0.4.8 link the first zip, so Windows must sort first
assert sorted([MAC["name"], WIN["name"], TXT["name"]])[0] == WIN["name"]

assert parse_version("v1.2.3") == (1, 2, 3)
assert parse_version("1.10.0") > parse_version("1.9.9")
assert parse_version("nonsense") == (0,)

print("test_update ok")
