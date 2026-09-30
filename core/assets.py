"""Font and Storybook bundles taken from w3tu, repacked for the target game."""
from __future__ import annotations

from pathlib import Path

from .bundle import BundleFile, read_bundle, write_bundle
from .metastore import BundleLayout, build_metastore
from .paths import assets_dir

FONT_PATH = "gameplay\\gui_new\\swf\\witcher3\\fonts_en.redswf"


def font_bundle(font: str) -> Path:
    return assets_dir() / "fonts" / f"{font}.bundle"


def storybook_bundle() -> Path:
    return assets_dir() / "storybook.bundle"


def layout_background(name: str) -> Path:
    return assets_dir() / "layout_bg" / f"{name}.jpg"


def font_files(font: str) -> list[BundleFile]:
    files = [f for f in read_bundle(font_bundle(font)) if f.path == FONT_PATH]
    if not files:
        raise RuntimeError(f"ฟอนต์ {font} ไม่มีไฟล์ {FONT_PATH}")
    return files


def storybook_files(slot: str) -> list[BundleFile]:
    files = read_bundle(storybook_bundle())
    if slot != "tr":
        files = [BundleFile(f.path.replace("_tr.subs", f"_{slot}.subs"), f.data) for f in files]
    return files


def write_mod_content(content_dir: Path, files: list[BundleFile]) -> list[str]:
    """Write blob0.bundle + metadata.store; returns written file names."""
    content_dir.mkdir(parents=True, exist_ok=True)
    size, data_offset, entries = write_bundle(content_dir / "blob0.bundle", files)
    meta = build_metastore(BundleLayout("blob0.bundle", size, data_offset, entries))
    (content_dir / "metadata.store").write_bytes(meta)
    return ["blob0.bundle", "metadata.store"]
