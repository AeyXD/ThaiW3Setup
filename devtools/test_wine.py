"""Finding the game inside a Wine bottle: drive mapping, the bottle registry, and mods.settings."""
import os, sys, tempfile

if sys.platform == "win32":  # a bottle cannot exist here, and "c:" is not a legal file name on Windows
    print("test_wine skipped: Wine bottles only exist off Windows")
    raise SystemExit(0)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from core import game_detect, wine
from core.game_detect import EDITION_REMASTERED, identify
from core.report import _mods_settings_paths
from core.wine import Bottle, bottle_of


def make_bottle(name: str = "Witcher3") -> Bottle:
    """A prefix laid out the way CrossOver does, with C: and a second drive."""
    prefix = Path(tempfile.mkdtemp()) / name
    (prefix / "drive_c" / "users" / "crossover" / "Documents").mkdir(parents=True)
    (prefix / "dosdevices").mkdir()
    (prefix / "dosdevices" / "c:").symlink_to(prefix / "drive_c")
    extra = Path(tempfile.mkdtemp()) / "Games"
    extra.mkdir()
    (prefix / "dosdevices" / "d:").symlink_to(extra)
    return Bottle(prefix, "CrossOver")


def make_game(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "content" / "content0").mkdir(parents=True)
    exe = root / "bin" / "x64_dx12"
    exe.mkdir(parents=True)
    (exe / "witcher3.exe").write_bytes(b"")
    return root


def write_reg(bottle: Bottle, hive: str, sections: dict) -> None:
    text = ["WINE REGISTRY Version 2", ""]
    for key, values in sections.items():
        text.append("[" + key.replace("\\", "\\\\") + "] 1700000000")
        text.append("#time=1d000000000")
        for name, value in values.items():
            text.append(f'"{name}"="' + value.replace("\\", "\\\\") + '"')
        text.append("")
    (bottle.prefix / wine.HIVES[hive]).write_text("\n".join(text), encoding="utf-8")


# --- drive mapping -------------------------------------------------------
b = make_bottle()
# a mapped drive is a symlink, so compare what both sides resolve to
assert b.host_path(r"C:\Program Files") == (b.drive_c / "Program Files").resolve(), b.host_path(r"C:\Program Files")
assert b.host_path(r"D:\\") == (b.prefix / "dosdevices" / "d:").resolve()
assert b.host_path(r"Z:\nope") is None, "an unmapped drive is not a path on this Mac"
assert b.host_path("not a windows path") is None
(b.drive_c / "MixedCase").mkdir()
assert b.host_path(r"C:\mixedcase").is_dir(), "a differently cased folder still resolves"
assert b.host_path(r"C:\nothing\here") == (b.drive_c / "nothing" / "here").resolve(), "maps even when absent"

# --- registry ------------------------------------------------------------
write_reg(b, "user", {r"Software\Valve\Steam": {"SteamPath": r"C:\Program Files (x86)\Steam"}})
assert b.registry("user", r"Software\Valve\Steam", "SteamPath") == r"C:\Program Files (x86)\Steam"
assert b.registry("user", r"software\valve\steam", "steampath"), "keys and names are case insensitive"
assert b.registry("user", r"Software\Valve\Steam", "Missing") is None
assert b.registry("machine", r"Software\Valve\Steam", "SteamPath") is None, "wrong hive"

write_reg(b, "machine", {
    r"Software\Wow6432Node\GOG.com\Games\1207664663": {"gameName": "The Witcher 3: Wild Hunt",
                                                       "path": r"D:\GOG\The Witcher 3"},
    r"Software\Wow6432Node\GOG.com\Games\9999": {"gameName": "Cyberpunk 2077", "path": r"D:\GOG\Cyberpunk"},
})
assert sorted(b.registry_keys("machine", r"Software\Wow6432Node\GOG.com\Games")) == ["1207664663", "9999"]

# --- the whole search ----------------------------------------------------
steam = b.drive_c / "Program Files (x86)" / "Steam"
(steam / "steamapps").mkdir(parents=True)
(steam / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders" { "0" { "path" "D:\\\\SteamLibrary" } }')
(steam / "steamapps" / f"appmanifest_{game_detect.STEAM_APP_ID}.acf").write_text('"AppState" { "installdir" "The Witcher 3" }')
library = b.host_path(r"D:\SteamLibrary")
library.mkdir(parents=True)
(library / "steamapps").mkdir()
(library / "steamapps" / f"appmanifest_{game_detect.STEAM_APP_ID}.acf").write_text(
    '"AppState" { "installdir" "The Witcher 3 Remastered" }')
expected = make_game(library / "steamapps" / "common" / "The Witcher 3 Remastered")
gog_game = make_game(b.host_path(r"D:\GOG\The Witcher 3"))

orig_bottles, orig_version = wine.bottles, game_detect.exe_version
try:
    game_detect.bottles = wine.bottles = lambda: [b]
    game_detect.exe_version = lambda _p: "5.0.15.61352"
    steam_found = game_detect._bottle_steam()
    assert expected in steam_found, (expected, steam_found)
    assert gog_game in game_detect._bottle_gog(), game_detect._bottle_gog()

    if not game_detect.WINDOWS:
        games = {str(g.path): g for g in game_detect.find_games()}
        assert str(expected) in games, list(games)
        assert str(gog_game) in games, list(games)
        assert games[str(expected)].store == "Steam" and games[str(gog_game)].store == "GOG"
        assert all(g.edition == EDITION_REMASTERED for g in games.values())

    # --- mods.settings lives in the bottle, not in the Mac's home --------
    # the game sits on D:, outside drive_c, so bottle_of has to match it through the drive mapping
    found = bottle_of(expected)
    assert found is not None and found.prefix.resolve() == b.prefix.resolve(), found
    assert bottle_of(Path(tempfile.mkdtemp())) is None
    docs = (b.drive_c / "users" / "crossover" / "Documents").resolve()
    assert [d.resolve() for d in b.documents_dirs()] == [docs], b.documents_dirs()

    paths = _mods_settings_paths(identify(expected))
    assert paths[0].resolve() == docs / "The Witcher 3" / "mods.settings", paths
finally:
    game_detect.bottles = wine.bottles = orig_bottles
    game_detect.exe_version = orig_version

# --- discovery: WINEPREFIX, a folder of bottles, and Heroic's pfx layout -
env = make_bottle("FromEnv")
os.environ["WINEPREFIX"] = str(env.prefix)
try:
    assert [b.prefix for b in wine.bottles()] == [env.prefix], wine.bottles()
finally:
    del os.environ["WINEPREFIX"]

folder = Path(tempfile.mkdtemp())
(folder / "Flat" / "drive_c").mkdir(parents=True)
(folder / "Heroic game" / "pfx" / "drive_c").mkdir(parents=True)
(folder / "not a bottle").mkdir()
found = sorted(b.prefix.name for b in wine._prefixes_under(folder, "CrossOver"))
assert found == ["Flat", "pfx"], found

single = Path(tempfile.mkdtemp())
(single / "drive_c").mkdir()
assert wine._prefixes_under(single, "Wine") == [wine.Bottle(single, "Wine")], "a root can be the prefix itself"

print("test_wine ok")
