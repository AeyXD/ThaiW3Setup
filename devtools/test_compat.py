"""Thai patches for other UI mods (Ink and Iron): fonts, sources, status, install order, Mod Manager zip."""
import os, re, shutil, sys, tempfile, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from core import compat, game_detect, installer, mods_settings
from core.assets import FONT_PATH, font_files
from core.bundle import iter_bundle
from core.abc_patch import _u30, string_pool
from core.assets import write_mod_content
from core.bundle import BundleFile
from core.compat import (COMPAT_MODS, DISABLED, MISSING, NO_PATCH, OK, ORPHAN, OVERLAP, PRIORITY, STALE,
                         open_sources, patch_files, patch_info, patch_status, patched_paths, write_patch_info)
from core.compat_text import (GWENT_OPPONENT_NAME_DTY, GWENT_PLAYER_NAME_DTY, GWENT_SCORE_DTY,
                              INK_AND_IRON_TITLE, _loc_rows, _parse_place_matrix, _symbol_classes,
                              _u30_bytes, align_gwent_hud, shift_game_version, translate_abc,
                              translate_swf, translator)
from core.swf_font import _swf_body, _tags
from core.game_detect import identify
from core.installer import InstallReport, _confirm_compat, _require_compat_sources, export_patch_zip, uninstall
from core.mods_settings import ModSetting, loses_to, parse
from core.options import InstallOptions
from core.swf_font import load_fonts, merge_glyphs

IAI = Path(r"C:\Users\saetanpee\Downloads\Ink and Iron - All in One 13111 0.7.2 2026-10-07T15-45Z Ukn0RyGRl")
PARTS = ("modInkAndIronDialogue", "modInkAndIronFonts", "modInkAndIronHUD")
MOD = COMPAT_MODS["inkandiron"]

# mods.settings: lower Priority wins, unlisted mods load after listed ones
s = parse("[modInkAndIronUI]\nEnabled=1\nPriority=3\n\n[mod0000_ThaiPatch_InkAndIron]\nEnabled=0\nPriority=9\n")
assert s["modinkandironui"] == ModSetting(True, 3) and s["mod0000_thaipatch_inkandiron"] == ModSetting(False, 9)
assert loses_to("mod0000_ThaiPatch_InkAndIron", ["modInkAndIronUI", "modInkAndIronHUD"], s) == ["modInkAndIronUI"]
assert loses_to("mod0000_ThaiPatch_InkAndIron", ["modInkAndIronUI"], {}) == [], "name order: mod0000_ wins"
assert loses_to("mod0000_X", ["modA"], parse("[modA]\nPriority=1\n")) == ["modA"], "listed beats unlisted"
assert parse("not ini at all [") == {}

# every step list has a step for each state that needs the player to act
for steps in (MOD.direct_steps, MOD.manager_steps):
    covered = set().union(*(st.states for st in steps))
    assert {NO_PATCH, STALE, PRIORITY, DISABLED} <= covered, covered
assert compat.PatchStatus(MOD, MISSING).step() == 0
assert compat.PatchStatus(MOD, NO_PATCH).step() == 1
assert compat.PatchStatus(MOD, OVERLAP).step() == 1
assert compat.PatchStatus(MOD, NO_PATCH).step(MOD.manager_steps) == 1
assert compat.PatchStatus(MOD, OVERLAP).step(MOD.manager_steps) == 3
assert compat.PatchStatus(MOD, OK).step() is None
assert compat.PatchStatus(MOD, NO_PATCH).short == "ต้องทำแพตช์"
assert compat.PatchStatus(MOD, NO_PATCH).next_action()[2] == "install"
readme = compat.patch_readme(MOD, {"sources": {}, "created": "", "font": ""})
assert compat.MAKE_ZIP not in readme and MOD.zip_name in readme, readme

# a mod's own label rows: EN and TR entries point at the Thai, the same string used as a key stays
assert _u30_bytes(5, 2) == b"\x85\x00" and _u30(b"\x85\x00", 0) == (5, 2)
pool = [b"EN", b"Hide card", b"PL", b"Ukryj", b"TR", b"Kart\xc4\xb1 gizle"]
code = bytes([0x2C, 1, 0x2C, 2, 0x2C, 3, 0x2C, 4, 0x2C, 5, 0x2C, 6, 0x2C, 2])
abc = (b"\0\0\0\0" + b"\0" + b"\x10\0\x2e\0" + b"\0\0\0" + bytes([len(pool) + 1])
       + b"".join(bytes([len(s)]) + s for s in pool) + b"\0\0\0" + code)
new, count = translate_abc(abc, {"Hide card": "ซ่อนการ์ด"})
assert count == 2, count
start, spans, end = string_pool(new, 5)
strings = [""] + [new[a:b].decode() for a, b in spans]
assert strings[:7] == [""] + [s.decode() for s in pool] and strings[7].replace("\u200a", "") == "ซ่อนการ์ด"
assert new[end + 3:] == bytes([0x2C, 1, 0x2C, 7, 0x2C, 3, 0x2C, 4, 0x2C, 5, 0x2C, 7, 0x2C, 2]), new[end + 3:]
assert translate_abc(abc, {}) is None
# a title outside any row is replaced in the pool itself, so every use of it changes
new, count = translate_abc(abc, {}, {"Ukryj": "ซ่อน"})
_, spans, end = string_pool(new, 5)
assert count == 1 and new[spans[3][0]:spans[3][1]].decode() == "ซ่อน" and len(spans) == len(pool)
assert new[end + 3:] == code

if not IAI.is_dir():
    print("test_compat ok (Ink and Iron download not found, file tests skipped)")
    sys.exit(0)

fonts_bundle = IAI / "mods" / "modInkAndIronFonts" / "content" / "blob0.bundle"
iai_font = next(iter_bundle(fonts_bundle, lambda n, _s: n == FONT_PATH)).data
merged = load_fonts(merge_glyphs(iai_font, font_files("Sarabun")[0].data))
assert len(merged) == 7 and {f.name for f in merged} >= {"IM Fell English", "IM Fell English SC"}
for f in merged:
    assert all(c in f.glyphs for c in range(0xE01, 0xE3B)), f.name

orig_exe, orig_paths = game_detect.exe_version, mods_settings.settings_paths
game_detect.exe_version = lambda _p: "5.0.15.61352"
tmp = Path(tempfile.mkdtemp())
settings_file = tmp / "mods.settings"
mods_settings.settings_paths = lambda _g=None: [settings_file]
try:
    root = tmp / "game"
    (root / "content" / "content0").mkdir(parents=True)
    (root / "bin" / "x64_dx12").mkdir(parents=True)
    (root / "bin" / "x64_dx12" / "witcher3.exe").write_bytes(b"")
    mods = root / "mods"
    mods.mkdir()
    g = identify(root)
    assert patch_status(mods, MOD, {}).state == MISSING

    # a downloaded zip with the usual mods/<part>/content layout, and the same as an unpacked folder
    download = tmp / "download"
    for part in PARTS:
        shutil.copytree(IAI / "mods" / part, download / "mods" / part)
    zpath = tmp / "iai.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for f in download.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(download).as_posix())
    for source in (zpath, download):
        with open_sources(MOD, mods, source) as src:
            assert sorted(src.bundles) == list(PARTS), src.bundles
    try:
        with open_sources(MOD, mods, None):
            raise AssertionError("no sources expected")
    except FileNotFoundError:
        pass
    try:
        with open_sources(MOD, mods, tmp / "iai.7z"):
            raise AssertionError("7z is not readable")
    except ValueError:
        pass

    # the patch for a game with the parts installed
    for part in PARTS:
        shutil.copytree(download / "mods" / part, mods / part)
    assert patch_status(mods, MOD, {}).state == NO_PATCH
    with open_sources(MOD, mods) as src:
        assert src.origin == str(mods)
        files, warnings = patch_files(src, "Sarabun", thai_logo=True)
        info = patch_info(src, "Sarabun", True)
    paths = {f.path for f in files}
    assert FONT_PATH in paths and "gameplay\\gui_new\\swf\\hud\\hud_dialog.redswf" in paths, paths
    dialog = next(f.data for f in files if f.path.endswith("hud_dialog.redswf"))
    labels = {}
    shop_labels = {}
    for tag, d in _tags(_swf_body(dialog)):
        if tag == 82:
            _, spans, end = string_pool(d, d.index(b"\0", 4) + 1)
            strings = [""] + [d[a:b].decode("utf-8", "replace") for a, b in spans]
            plain = {s: re.sub(r"<[^>]+>", "", s).replace("\u200a", "") for s in strings}
            labels.update({e.code: strings[e.value] for row in _loc_rows(d, strings, end) for e in row
                           if plain[strings[e.value]] == "เดินทางเร็ว"})
            shop_labels.update({e.code: strings[e.value] for row in _loc_rows(d, strings, end) for e in row
                                if "ร้าน" in plain[strings[e.value]]})
    assert set(labels) == {"EN", "TR"}, labels
    assert set(shop_labels) == {"EN", "TR"}, shop_labels
    assert all("<" not in v and ">" not in v for v in shop_labels.values()), shop_labels

    # Option.iaiDecor places iaiMark with (lineH - markH) * 0.6; Thai reads low, so center at 0.5
    from core.compat_text import MARK_Y_FACTOR_FROM, MARK_Y_FACTOR_TO, _mark_y_factor_sites
    orig_dialog = next(iter_bundle(IAI / "mods" / "modInkAndIronDialogue" / "content" / "blob0.bundle",
                                   lambda n, _: n.endswith("hud_dialog.redswf"))).data
    assert _mark_y_factor_sites(_swf_body(orig_dialog), MARK_Y_FACTOR_FROM)
    assert not _mark_y_factor_sites(_swf_body(orig_dialog), MARK_Y_FACTOR_TO)
    assert _mark_y_factor_sites(_swf_body(dialog), MARK_Y_FACTOR_TO)
    assert not _mark_y_factor_sites(_swf_body(dialog), MARK_Y_FACTOR_FROM)

    # menu logo titles: Thai with letterSpacing 0 (Ink and Iron uses 9 / 12 for Latin tracking)
    from core.abc_patch import DO_ABC, _u30 as read_u30
    from core.compat_text import OP_PUSHSTRING
    from core.swf_font import _swf_body, _tags
    menu = next(iter_bundle(IAI / "mods" / "modInkAndIronUI" / "content" / "blob0.bundle",
                            lambda n, _: "panel_ingamemenu" in n))
    body = _swf_body(menu.data)
    patched = translate_swf(body, {}, INK_AND_IRON_TITLE)
    assert patched is not None
    spacings = []
    for tag, d in _tags(patched):
        if tag != DO_ABC:
            continue
        i = d.index(b"\0", 4) + 1
        start, spans, end = string_pool(d, i)
        strings = [""] + [d[a:b].decode("utf-8", "replace") for a, b in spans]
        assert "เดอะ วิทเชอร์" in strings and "ไวลด์ ฮันท์" in strings
        assert "\u200a" not in "เดอะ วิทเชอร์" and all("\u200a" not in s for s in strings
                                                         if s in INK_AND_IRON_TITLE.values())
        font = next(n for n, s in enumerate(strings) if s == "$TitleFont")
        for title in INK_AND_IRON_TITLE.values():
            idx = strings.index(title)
            needle = bytes([OP_PUSHSTRING]) + _u30_bytes(idx)
            font_needle = bytes([OP_PUSHSTRING]) + _u30_bytes(font)
            p = end
            while True:
                p = d.find(needle, p)
                if p < 0:
                    break
                font_at = d.find(font_needle, p + len(needle), p + len(needle) + 24)
                if font_at >= 0:
                    j = font_at + len(font_needle)
                    for k in range(j, min(len(d) - 4, j + 64)):
                        if d[k] == 0x24 and d[k + 2] in (0x46, 0x4F):
                            _, q = read_u30(d, k + 3)
                            if q < len(d) and d[q] == 9:
                                spacings.append(d[k + 1])
                                break
                p += 1
    assert spacings and all(s == 0 for s in spacings), spacings

    # game version (txtVersion): nudged right so it clears the wider Thai logo title
    def _version_xy(swf: bytes, name: bytes = b"txtVersion\0"):
        found = []
        def walk(data: bytes, root=True):
            import struct
            if root:
                nbits = data[0] >> 3
                p = (5 + 4 * nbits + 7) // 8 + 4
            else:
                p = 0
            while p + 2 <= len(data):
                code_len = struct.unpack_from("<H", data, p)[0]
                tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
                if ln == 0x3F:
                    ln = struct.unpack_from("<I", data, hp)[0]
                    hp += 4
                if tag == 39 and hp + 4 <= hp + ln:
                    walk(data[hp + 4:hp + ln], False)
                elif tag == 26 and name in data[hp:hp + ln]:
                    parsed = _parse_place_matrix(data[hp:hp + ln])
                    if parsed:
                        found.append(parsed[2:4])
                p = hp + ln
                if tag == 0:
                    break
        walk(swf)
        return found
    before = _version_xy(body)
    titled = translator({}, INK_AND_IRON_TITLE)(body)
    assert titled is not None and shift_game_version(body) is not None
    after = _version_xy(titled)
    assert before and after and len(before) == len(after)
    assert all(ax > bx and ay == by for (bx, by), (ax, ay) in zip(before, after)), (before, after)

    # Gwent HUD: opponent name down, player name up, score digits nudged in their banners
    import struct
    gwent_bundle = IAI / "mods" / "modInkAndIronGwent" / "content" / "blob0.bundle"
    gwent_body = _swf_body(next(iter_bundle(gwent_bundle, lambda n, _: n.endswith("gwint_game.redswf"))).data)
    symbols = _symbol_classes(gwent_body)
    assert any(n.rsplit(".", 1)[-1] == "PlayerRendererOpponent" for n in symbols.values())

    def _gwent_places(swf: bytes):
        found = []
        def walk(data: bytes, root=True, sid=None):
            p = ((5 + 4 * (data[0] >> 3) + 7) // 8 + 4) if root else 0
            while p + 2 <= len(data):
                code_len = struct.unpack_from("<H", data, p)[0]
                tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
                if ln == 0x3F:
                    ln = struct.unpack_from("<I", data, hp)[0]
                    hp += 4
                payload = data[hp:hp + ln]
                if tag == 39 and len(payload) >= 4:
                    walk(payload[4:], False, struct.unpack_from("<H", payload, 0)[0])
                elif tag == 26:
                    for needle, label in ((b"txtPlayerName\0", "name"), (b"txtFactionName\0", "faction"),
                                          (b"txtScore\0", "score")):
                        if needle in payload:
                            mat = _parse_place_matrix(bytearray(payload))
                            if mat:
                                found.append((sid, label, mat[2], mat[3]))
                p = hp + ln
                if tag == 0:
                    break
        walk(swf)
        return found

    gwent_before = {(sid, kind): (tx, ty) for sid, kind, tx, ty in _gwent_places(gwent_body)}
    gwent_aligned = align_gwent_hud(gwent_body)
    assert gwent_aligned is not None
    gwent_after = {(sid, kind): (tx, ty) for sid, kind, tx, ty in _gwent_places(gwent_aligned)}
    assert gwent_before.keys() == gwent_after.keys()
    for (sid, kind), (tx0, ty0) in gwent_before.items():
        tx1, ty1 = gwent_after[(sid, kind)]
        assert tx0 == tx1, (sid, kind, tx0, tx1)
        short = symbols.get(sid, "").rsplit(".", 1)[-1]
        if kind == "score":
            assert ty1 - ty0 == GWENT_SCORE_DTY, (sid, ty0, ty1)
        elif short == "PlayerRendererOpponent":
            assert ty1 - ty0 == GWENT_OPPONENT_NAME_DTY, (sid, kind, ty0, ty1)
        elif short == "PlayerRenderer":
            assert ty1 - ty0 == GWENT_PLAYER_NAME_DTY, (sid, kind, ty0, ty1)
        else:
            raise AssertionError(f"unexpected place {sid} {kind} {short}")
    # other SWFs without Gwent sprites are unchanged
    assert align_gwent_hud(body) is None

    # the main Thai mods leave the mod's files to a patch, never when there is no patch at all
    assert patched_paths(mods, {}, set(), set()) == set()
    leave = patched_paths(mods, {}, {"inkandiron"}, set())
    assert FONT_PATH in leave and "gameplay\\gui_new\\swf\\hud\\hud_dialog.redswf" in leave
    assert patched_paths(mods, parse("[modInkAndIronFonts]\nEnabled=0\n"), {"inkandiron"}, set()) <= leave
    patch = mods / MOD.patch
    (patch / "content").mkdir(parents=True)
    write_patch_info(patch, info)
    assert patched_paths(mods, {}, set(), set()) == leave, "a patch from the Mod Manager counts"
    assert patched_paths(mods, {}, set(), {MOD.patch}) == set(), "our own old patch is about to go"
    assert patch_status(mods, MOD, {}, "Sarabun").state == OK
    write_mod_content(mods / installer.MOD_FONT / "content", [BundleFile(FONT_PATH, b"x")])
    st = patch_status(mods, MOD, {}, "Sarabun", (installer.MOD_FONT, installer.MOD_LOGO))
    assert st.state == OVERLAP and st.ahead == [FONT_PATH], st
    shutil.rmtree(mods / installer.MOD_FONT)
    assert patch_status(mods, MOD, {}, "Sarabun", (installer.MOD_FONT, installer.MOD_LOGO)).state == OK
    assert patch_status(mods, MOD, {}, "Prompt").state == STALE, "another Thai font"
    write_patch_info(patch, {**info, "texts": "older"})
    assert patch_status(mods, MOD, {}, "Sarabun").state == STALE, "built with an older translation table"
    write_patch_info(patch, info)
    assert patch_status(mods, MOD, parse(f"[{MOD.patch}]\nEnabled=0\n")).state == DISABLED
    st = patch_status(mods, MOD, parse("[modInkAndIronHUD]\nPriority=0\n"))
    assert st.state == PRIORITY and st.ahead == ["modInkAndIronHUD"], st
    assert patch_status(mods, MOD, parse(f"[modInkAndIronHUD]\nPriority=2\n[{MOD.patch}]\nPriority=0\n")).state == OK
    with open(mods / "modInkAndIronHUD" / "content" / "blob0.bundle", "ab") as fh:
        fh.write(b"\0")
    assert patch_status(mods, MOD, {}).state == STALE, "the mod was updated"
    assert patch_status(mods, MOD, parse("[modInkAndIronHUD]\nEnabled=0\n")).state == STALE, "a part switched off"

    # toggles decide patches: off = never auto-add; on = include (ask only if a foreign patch would be replaced)
    asked = []
    report = InstallReport()
    keys = _confirm_compat(g, InstallOptions(str(root)), lambda m: asked.append(m) or False, report)
    assert keys == [] and asked == [], "toggle off: do not ask to add a patch"
    keys = _confirm_compat(g, InstallOptions(str(root), compat=["inkandiron"]), lambda m: asked.append(m) or False,
                           report)
    assert keys == [] and len(asked) == 1, "toggle on + foreign patch: ask before replacing"
    shutil.rmtree(patch)
    asked.clear()
    keys = _confirm_compat(g, InstallOptions(str(root), compat=["inkandiron"]), lambda m: asked.append(m) or True,
                           report)
    assert keys == ["inkandiron"] and asked == [], "toggle on + mod in game: patch immediately"
    keys = _confirm_compat(g, InstallOptions(str(root)), lambda m: True, report)
    assert keys == [], "toggle off + mod in game: still Thai-only"
    assert _require_compat_sources(g, InstallOptions(str(root), compat=["inkandiron"])) == ["inkandiron"]
    uninstall(root)
    assert (mods / "modInkAndIronHUD").is_dir()

    # missing mod and no zip/folder → hard fail; zip source is enough
    for part in PARTS:
        shutil.rmtree(mods / part)
    try:
        _confirm_compat(g, InstallOptions(str(root), compat=["inkandiron"]), lambda m: True, report)
        raise AssertionError("missing source should fail")
    except RuntimeError:
        pass
    keys = _confirm_compat(g, InstallOptions(str(root), compat=["inkandiron"],
                                             compat_sources={"inkandiron": str(zpath)}),
                           lambda m: True, report)
    assert keys == ["inkandiron"]
    for part in PARTS:
        shutil.copytree(download / "mods" / part, mods / part)

    # Mod Manager zip from the game's copy (patch-only helper still works)
    out = tmp / "out"
    out.mkdir()
    r = export_patch_zip(InstallOptions(str(root)), "inkandiron", out)
    names = zipfile.ZipFile(r.output).namelist()
    for want in (f"mods/{MOD.patch}/content/blob0.bundle", f"mods/{MOD.patch}/content/metadata.store",
                 f"mods/{MOD.patch}/{compat.PATCH_INFO}", installer.PATCH_README):
        assert want in names, (want, names)

    # orphan patch, and uninstall only removes a patch our manifest lists
    for part in PARTS:
        shutil.rmtree(mods / part)
    (patch / "content").mkdir(parents=True)
    write_patch_info(patch, info)
    assert patch_status(mods, MOD, {}).state == ORPHAN
    uninstall(root)
    assert patch.is_dir(), "a patch from the Mod Manager stays"
    (mods / installer.MOD_TEXT).mkdir()
    (mods / installer.MOD_TEXT / installer.MANIFEST).write_text(f'{{"mods": ["{MOD.patch}"]}}', encoding="utf-8")
    assert MOD.patch in uninstall(root) and not patch.exists()

    # the user's choices survive a settings round trip and bad ones are refused
    InstallOptions(compat=["inkandiron"], compat_sources={"inkandiron": str(zpath)}).validate()
    for bad in (InstallOptions(compat=["nope"]), InstallOptions(compat_sources={"nope": "x"})):
        try:
            bad.validate()
            raise AssertionError("invalid compat options accepted")
        except ValueError:
            pass
finally:
    game_detect.exe_version, mods_settings.settings_paths = orig_exe, orig_paths
    shutil.rmtree(tmp, ignore_errors=True)
print("test_compat ok")
