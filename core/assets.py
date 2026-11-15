"""Font and Storybook bundles taken from w3tu, repacked for the target game."""
from __future__ import annotations

from pathlib import Path

from .bundle import BundleFile, read_bundle, write_bundle
from .metastore import BundleLayout, build_metastore
from .paths import assets_dir
from .swf_font import add_empty_glyph, alias_glyphs
from .thai_wrap import BREAK, NBSP

FONT_PATH = "gameplay\\gui_new\\swf\\witcher3\\fonts_en.redswf"
# the Turkish slot's case mapping turns i into İ and I into ı; Thai text never needs either
TURKISH_I = {0x130: ord("I"), 0x131: ord("i")}
# the fonts' own no-break space is up to twice as wide as a space; draw it as a space (thai_wrap.NBSP)
GLYPH_ALIASES = {**TURKISH_I, ord(NBSP): ord(" ")}


def font_bundle(font: str) -> Path:
    return assets_dir() / "fonts" / f"{font}.bundle"


def storybook_bundle() -> Path:
    return assets_dir() / "storybook.bundle"


def layout_background(name: str) -> Path:
    return assets_dir() / "layout_bg" / f"{name}.jpg"


def help_image(name: str) -> Path:
    return assets_dir() / "help" / f"{name}.jpg"


def font_files(font: str) -> list[BundleFile]:
    files = [BundleFile(f.path, alias_glyphs(add_empty_glyph(f.data, ord(BREAK)), GLYPH_ALIASES))
             for f in read_bundle(font_bundle(font)) if f.path == FONT_PATH]
    if not files:
        raise RuntimeError(f"ฟอนต์ {font} ไม่มีไฟล์ {FONT_PATH}")
    return files


def storybook_files(slot: str = "tr") -> list[BundleFile]:
    """Cutscene .subs follow TextLanguage, not the w3strings slot.

    Ship both ``_tr.subs`` and ``_en.subs`` so Thai shows whether the player
    picked the Turkish slot (recommended) or the English slot (Xbox).
    ``slot`` is kept for call-site compatibility and ignored.
    """
    _ = slot  # TextLanguage may differ from the installed w3strings slot
    files = read_bundle(storybook_bundle())
    en = [BundleFile(f.path.replace("_tr.subs", "_en.subs"), f.data) for f in files]
    return [*files, *en]


def write_mod_content(content_dir: Path, files: list[BundleFile]) -> list[str]:
    """Write blob0.bundle + metadata.store; returns written file names."""
    content_dir.mkdir(parents=True, exist_ok=True)
    size, data_offset, entries = write_bundle(content_dir / "blob0.bundle", files)
    meta = build_metastore(BundleLayout("blob0.bundle", size, data_offset, entries))
    (content_dir / "metadata.store").write_bytes(meta)
    return ["blob0.bundle", "metadata.store"]
