"""Other Thai mods (ThaiLanguage Remastered on Nexus), HUD script overlaps, loose content files, tampered files."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from core import game_detect, installer
from core.game_detect import identify
from core.installer import (DISABLED_DIR, disable_mods, foreign_thai_mods, modified_files, script_overlaps,
                            strings_have_thai, _file_hashes)
from core.report import _conflicts
from core.w3strings import W3Strings

NEXUS = Path(r"C:\Users\saetanpee\Downloads\ThaiLanguage Remastered 5.0 13027 1 2026-09-29T15-50Z XMCm1uHJN\mods")


def make_game() -> Path:
    p = Path(tempfile.mkdtemp())
    (p / "content" / "content0").mkdir(parents=True)
    (p / "bin" / "x64_dx12").mkdir(parents=True)
    (p / "bin" / "x64_dx12" / "witcher3.exe").write_bytes(b"")
    return p


orig = game_detect.exe_version
game_detect.exe_version = lambda _p: "5.0.15.61352"
try:
    root = make_game()
    mods = root / "mods"
    hud = Path("content/scripts/game/gui/hud/modules")
    (mods / "modThaiLanguage" / hud).mkdir(parents=True)
    (mods / "modThaiLanguage" / hud / "hudModuleSubtitles.ws").write_text("x")
    (mods / "modThaiFont" / "content").mkdir(parents=True)
    (mods / "modThaiFont" / "content" / "blob0.bundle").write_bytes(b"ours")
    (mods / "modSomethingElse" / "content").mkdir(parents=True)
    (mods / "modSomethingElse" / "content" / "en.w3strings").write_bytes(b"not a real file")
    (mods / "modRenamedThai" / "content").mkdir(parents=True)
    thai = W3Strings(language="tr", version=164, strings={i: f"ข้อความภาษาไทย {i}" for i in range(1, 400)},
                     keys={1: 0x1234})
    thai.save(mods / "modRenamedThai" / "content" / "tr.w3strings")
    (root / "content" / "blob0.bundle").write_bytes(b"")
    (root / "content" / "tr.w3strings").write_bytes(b"")
    (root / "content" / "scripts").mkdir()

    g = identify(root)
    assert g.loose_content == ["blob0.bundle", "scripts", "tr.w3strings"], g.loose_content
    assert any("content" in n and "blob0.bundle" in n for n in g.notes), g.notes

    assert [p.name for p in foreign_thai_mods(g)] == ["modThaiLanguage"], "name match only without deep"
    assert strings_have_thai(mods / "modRenamedThai" / "content" / "tr.w3strings", "tr")
    assert [p.name for p in foreign_thai_mods(g, deep=True)] == ["modRenamedThai", "modThaiLanguage"]
    assert script_overlaps(g) == ["modThaiLanguage (hudModuleSubtitles.ws)"], script_overlaps(g)

    conflicts = _conflicts(g)
    for part in ("loose in content", "other Thai mod: mods\\modThaiLanguage", "same HUD scripts"):
        assert any(part in c for c in conflicts), (part, conflicts)

    hashes = _file_hashes(mods, ["modThaiFont"])
    assert modified_files(g, hashes) == []
    (mods / "modThaiFont" / "content" / "blob0.bundle").write_bytes(b"someone else's font")
    assert modified_files(g, hashes) == ["modThaiFont/content/blob0.bundle"]

    (root / DISABLED_DIR / "modThaiLanguage").mkdir(parents=True)
    target = disable_mods(g, foreign_thai_mods(g, deep=True))
    assert not (mods / "modThaiLanguage").exists() and not (mods / "modRenamedThai").exists()
    moved = sorted(p.name for p in target.iterdir())
    assert "modRenamedThai" in moved and len([n for n in moved if n.startswith("modThaiLanguage")]) == 2, moved
    assert foreign_thai_mods(g, deep=True) == [] and script_overlaps(g) == []

    if NEXUS.is_dir():
        nexus = NEXUS / "modThaiLanguage" / "content" / "tr.w3strings"
        assert strings_have_thai(nexus, "tr")
finally:
    game_detect.exe_version = orig
print("test_conflicts ok")
