"""Edition detection: exe version decides; leftover 4.x content folders only warn."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from core import game_detect
from core.game_detect import EDITION_CLASSIC, EDITION_NEXTGEN, EDITION_REMASTERED, identify

GAME = r"D:\SteamLibrary\steamapps\common\The Witcher 3"


def make_game(split: int = 0, launcher: bool = True, dx12: bool = True) -> Path:
    p = Path(tempfile.mkdtemp())
    for i in range(split + 1):
        (p / "content" / f"content{i}").mkdir(parents=True)
    (p / "content" / "content0" / "en.w3strings").write_bytes(b"")
    (p / "content" / "content3" if split >= 3 else p / "content" / "content0").joinpath("tr.w3strings").write_bytes(b"")
    exe = p / "bin" / ("x64_dx12" if dx12 else "x64")
    exe.mkdir(parents=True)
    (exe / "witcher3.exe").write_bytes(b"")
    if launcher:
        (p / "launcher-configuration.json").write_text(json.dumps({"editions": [{"name": "remasteredEdition"}]}))
    return p


real = identify(GAME)
assert real.edition == EDITION_REMASTERED and real.version.startswith("5."), (real.edition, real.version)
assert not real.stale_content

orig = game_detect.exe_version
try:
    # the reported case: 5.0 exe, content1-content12 left over from 4.x
    game_detect.exe_version = lambda _p: "5.0.15.58680"
    g = identify(make_game(split=12))
    assert g.edition == EDITION_REMASTERED, g.edition
    assert g.stale_content == [f"content{i}" for i in range(1, 13)], g.stale_content
    assert "content1-content12" in g.notes[0], g.notes
    assert all(f.parent.name == "content0" for f in g.strings_files("tr")), g.strings_files("tr")

    g = identify(make_game(split=12, launcher=False))
    assert g.edition == EDITION_REMASTERED, "exe version outranks launcher-configuration.json"

    # Xbox app layout: the picked folder holds Content\ with bin\ and content\ inside
    xbox = Path(tempfile.mkdtemp()) / "The Witcher 3- Wild Hunt - Game of the Year Edition"
    xbox.mkdir()
    make_game().rename(xbox / "Content")
    g = identify(xbox)
    assert g.edition == EDITION_REMASTERED and g.path == xbox / "Content", (g.edition, g.path)
    assert g.mods_dir == xbox / "Content" / "mods"
    assert game_detect.game_root(xbox / "Content") == xbox / "Content"

    game_detect.exe_version = lambda _p: "4.4.0.0"
    g = identify(make_game(split=12))
    assert g.edition == EDITION_NEXTGEN and not g.notes, (g.edition, g.notes)
    assert len(g.strings_files("en")) == 1 and len(g.strings_files("tr")) == 1

    game_detect.exe_version = lambda _p: "3.2.0.0"
    assert identify(make_game(dx12=False)).edition == EDITION_CLASSIC

    # no version resource: fall back to launcher-configuration.json + layout
    game_detect.exe_version = lambda _p: ""
    assert identify(make_game()).edition == EDITION_REMASTERED
    assert identify(make_game(split=12)).edition == EDITION_NEXTGEN
    assert identify(make_game(launcher=False)).edition == EDITION_NEXTGEN
finally:
    game_detect.exe_version = orig
print("test_detect ok")
