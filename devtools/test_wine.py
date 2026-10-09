"""Finding the game inside a Wine bottle: drive mapping, the bottle registry, and mods.settings."""
import os, sys, tempfile

if sys.platform == "win32":  # a bottle cannot exist here, and "c:" is not a legal file name on Windows
    print("test_wine skipped: Wine bottles only exist off Windows")
    raise SystemExit(0)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json, plistlib
from pathlib import Path
from core import game_detect, wine
from core.game_detect import EDITION_REMASTERED, identify
from core.report import _mods_settings_paths
from core.wine import Bottle, bottle_of

# the maintained Whisky fork and Heroic 2.x keep their prefixes somewhere the first version never looked
static_roots = [str(r) for r, _k in wine.BOTTLE_ROOTS]
assert str(wine.CONTAINERS / "com.franke.Whisky" / "Bottles") in static_roots, static_roots
assert str(wine.HOME / "Games/Heroic/Prefixes") in static_roots, static_roots

# from here on only what each test lays out counts, not the bottles on the machine running it
fake_home = Path(tempfile.mkdtemp())
wine.BOTTLE_ROOTS = ()
wine.CONTAINERS = fake_home / "Containers"
wine.HEROIC_DIR = fake_home / "heroic"


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

single = Path(tempfile.mkdtemp())
(single / "drive_c").mkdir()
assert wine.Bottle(single, "Wine").name == single.name, "no Metadata.plist: the folder name"


def make_prefix(path: Path, played: bool = False) -> Path:
    """A prefix whose Z: maps the whole disk, as every launcher sets up; the game then runs from outside."""
    docs = path / "drive_c" / "users" / "crossover" / "Documents"
    docs.mkdir(parents=True)
    (path / "drive_c" / "users" / "Public" / "Documents").mkdir(parents=True)
    if played:
        (docs / "The Witcher 3").mkdir()
    (path / "dosdevices").mkdir()
    (path / "dosdevices" / "c:").symlink_to("../drive_c")
    (path / "dosdevices" / "z:").symlink_to("/")
    return path


def file_url(path: Path) -> str:
    from urllib.parse import quote
    return "file://" + quote(str(path))


def use_launchers(home: Path) -> None:
    wine.CONTAINERS = home / "Containers"
    wine.HEROIC_DIR = home / "heroic"


case_insensitive = Path(str(fake_home).upper()).exists()
game_detect.exe_version = lambda _p: "5.0.15.65482"
try:
    # --- Whisky (the frankea fork): UUID folders, a pinned exe, and bottles listed in BottleVM.plist
    home = Path(tempfile.mkdtemp())
    use_launchers(home)
    fork = make_prefix(home / "Containers" / "com.franke.Whisky" / "Bottles" / "9DE9CA62-0F73-45D2")
    other = make_prefix(Path(tempfile.mkdtemp()) / "On Another Drive")
    game = make_game(Path(tempfile.mkdtemp()) / "games" / "w3")
    exe = game / "bin" / "x64_dx12" / "witcher3.exe"
    pinned = Path(str(exe).lower()) if case_insensitive else exe  # Whisky can record it lowercased
    (fork / "Metadata.plist").write_bytes(plistlib.dumps({"info": {"name": "TheWitcher3", "pins": [
        {"name": "The Witcher 3", "removable": False, "url": {"relative": file_url(pinned)}}]}}))
    for app, listed in (("com.isaacmarovitz.Whisky", other), ("com.franke.Whisky", fork)):
        (home / "Containers" / app).mkdir(parents=True, exist_ok=True)
        (home / "Containers" / app / "BottleVM.plist").write_bytes(
            plistlib.dumps({"paths": [{"relative": file_url(listed)}]}))

    found = wine.bottles()
    assert [b.prefix for b in found] == [other, fork], found
    assert found[1].label == "Whisky: TheWitcher3", found[1].label
    assert found[1].pinned_programs() == [exe], (found[1].pinned_programs(), exe)
    # both bottles reach the game through Z:, so the pin has to decide, not the order they were found in
    assert bottle_of(game).prefix == fork, bottle_of(game)
    docs = [d.parent.name for d in found[1].documents_dirs()]
    assert docs == ["crossover", "Public"], "the user's own Documents come before Public"

    games = game_detect.find_games()
    assert [(g.path, g.store) for g in games] == [(game, "Whisky")], [(g.path, g.store) for g in games]

    # --- Heroic 2.x: prefixes named after each game, games installed outside every prefix -----------
    home = Path(tempfile.mkdtemp())
    use_launchers(home)
    heroic = home / "heroic"
    prefixes = Path(tempfile.mkdtemp()) / "Prefixes"
    w3_prefix = make_prefix(prefixes / "The Witcher 3")
    played = make_prefix(prefixes / "Played Elsewhere", played=True)
    (heroic / "GamesConfig").mkdir(parents=True)
    # the shape Heroic 2.22.3 wrote: config.json, and one GamesConfig file per game keyed by its app name
    (heroic / "config.json").write_text(json.dumps({"defaultSettings": {
        "defaultWinePrefix": str(prefixes), "winePrefix": str(prefixes / "default")}}))
    (heroic / "GamesConfig" / "wfBDXaNbvbX5wstp7eiDdR.json").write_text(json.dumps({
        "wfBDXaNbvbX5wstp7eiDdR": {"winePrefix": str(w3_prefix), "wineVersion": {"type": "wine"}},
        "version": "v0", "explicit": True}))
    sideload = make_game(Path(tempfile.mkdtemp()) / "W3")
    gog = make_game(Path(tempfile.mkdtemp()) / "The Witcher 3 Wild Hunt GOTY")
    epic = make_game(Path(tempfile.mkdtemp()) / "TheWitcher3")
    mac_only = make_game(Path(tempfile.mkdtemp()) / "Mac build")
    (heroic / "sideload_apps").mkdir()
    (heroic / "sideload_apps" / "library.json").write_text(json.dumps({"games": [{
        "runner": "sideload", "app_name": "wfBDXaNbvbX5wstp7eiDdR", "title": "The Witcher 3",
        "install": {"executable": str(sideload / "bin" / "x64_dx12" / "witcher3.exe"), "platform": "Windows"},
        "folder_name": str(sideload / "bin" / "x64_dx12"), "is_installed": True}]}))
    (heroic / "gog_store").mkdir()
    (heroic / "gog_store" / "installed.json").write_text(json.dumps({"installed": [
        {"appName": "1207664663", "platform": "windows", "install_path": str(gog)},
        {"appName": "1", "platform": "osx", "install_path": str(mac_only)}]}))
    (heroic / "legendaryConfig" / "legendary").mkdir(parents=True)
    (heroic / "legendaryConfig" / "legendary" / "installed.json").write_text(json.dumps({
        "epicw3": {"app_name": "epicw3", "install_path": str(epic), "platform": "Windows"}}))

    labels = sorted(b.label for b in wine.bottles())
    assert labels == ["Heroic: Played Elsewhere", "Heroic: The Witcher 3"], labels
    installs = dict(wine.heroic_installs())
    assert installs[sideload / "bin" / "x64_dx12"] == w3_prefix, installs
    assert installs[gog] is None and installs[epic] is None and mac_only not in installs, installs

    games = {g.path: g.store for g in game_detect.find_games()}
    assert games == {sideload: "Heroic", gog: "Heroic", epic: "Heroic"}, games
    # Heroic says which prefix runs the sideloaded game, even though another one has run the game before
    assert bottle_of(sideload).prefix == w3_prefix, bottle_of(sideload)
    # nothing records where the GOG copy runs: the prefix the game has already written to is the best guess
    assert bottle_of(gog).prefix == played, bottle_of(gog)

    # --- GOG installed inside a bottle: the offline installer, and Galaxy for Windows ------------------
    home = Path(tempfile.mkdtemp())
    use_launchers(home)
    shelf = home / "Containers" / "com.franke.Whisky" / "Bottles"
    wine.BOTTLE_ROOTS = ((shelf, "Whisky"),)
    offline = make_prefix(shelf / "1111-OFFLINE")
    galaxy = make_prefix(shelf / "2222-GALAXY", played=True)  # Z: reaches the other bottle's game too

    def gog_reg(bottle: Path, folder: str) -> Path:
        """system.reg as Wine writes it after GOG's 32-bit installer ran: the key lands under Wow6432Node."""
        win = "C:\\" + folder
        reg = lambda s: s.replace("\\", "\\\\")
        (bottle / "system.reg").write_text("\n".join([
            "WINE REGISTRY Version 2", ";; All keys relative to REGISTRY\\\\Machine", "", "#arch=win64", "",
            "[Software\\\\Wow6432Node\\\\GOG.com\\\\Games\\\\1207664663] 1791531478", "#time=1dd57c11b1e6b9a",
            '"buildId"="58913412071462316"', '"dependsOn"=""',
            f'"exe"="{reg(win)}\\\\bin\\\\x64_dx12\\\\witcher3.exe"',
            '"gameID"="1207664663"', '"gameName"="The Witcher 3: Wild Hunt - Game of the Year Edition"',
            '"installDate"=dword:00000000', '"language"="English"', f'"path"="{reg(win)}"',
            f'"uninstallCommand"="{reg(win)}\\\\unins000.exe"', f'"workingDir"="{reg(win)}\\\\bin\\\\x64_dx12"', "",
            "[Software\\\\Wow6432Node\\\\GOG.com\\\\Games\\\\1423049311] 1791531478", "#time=1dd57c11b1e6b9a",
            '"gameName"="Cyberpunk 2077"', '"path"="C:\\\\GOG Games\\\\Cyberpunk 2077"', ""]), encoding="utf-8")
        return make_game(bottle / "drive_c" / folder)

    gog_offline = gog_reg(offline, "GOG Games\\The Witcher 3 Wild Hunt GOTY".replace("\\", "/")).resolve()
    gog_galaxy = gog_reg(galaxy, "Program Files (x86)/GOG Galaxy/Games/The Witcher 3 Wild Hunt GOTY").resolve()
    make_game(offline / "drive_c" / "GOG Games" / "Cyberpunk 2077")  # another GOG game is not ours

    games = [(g.path.resolve(), g.store) for g in game_detect.find_games()]
    # the offline copy also sits where _bottle_guesses looks, and must still be listed once, as GOG
    assert sorted(games) == sorted([(gog_offline, "GOG"), (gog_galaxy, "GOG")]), games
    assert bottle_of(gog_offline).prefix == offline.resolve(), "a game under drive_c belongs to that bottle, whatever Z: maps"
    assert bottle_of(gog_galaxy).prefix == galaxy.resolve()
    paths = _mods_settings_paths(identify(gog_offline))
    assert paths[0] == offline.resolve() / "drive_c/users/crossover/Documents/The Witcher 3/mods.settings", paths

    # copied in by hand, no installer: the registry knows nothing, the usual folder name still finds it
    (offline / "system.reg").unlink()
    games = [(g.path.resolve(), g.store) for g in game_detect.find_games()]
    assert (gog_offline, "") in games, games
    wine.BOTTLE_ROOTS = ()

    # --- a broken launcher file is skipped, not fatal ----------------------------------------------
    use_launchers(heroic.parent)
    (heroic / "config.json").write_text("{ not json")
    (heroic / "gog_store" / "installed.json").write_text("[]")
    assert sideload in {g.path for g in game_detect.find_games()}
finally:
    game_detect.exe_version = orig_version

if case_insensitive:
    mixed = Path(tempfile.mkdtemp()) / "MixedCase" / "Inner"
    mixed.mkdir(parents=True)
    assert str(wine._true_case(Path(str(mixed).lower()))).endswith("MixedCase/Inner")

print("test_wine ok")
