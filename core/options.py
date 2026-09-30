from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields

from .custom import LEGACY_TABS, NAME_DOUBLE, NAME_MODES, default_sheets, is_name_tab, name_label, sheet_key
from .paths import app_data_dir

log = logging.getLogger(__name__)

FONTS = {
    "CSPraKas": "CS PraKas",
    "Mahaniyom": "Mahaniyom",
    "Prompt": "Prompt",
    "Sarabun": "Sarabun",
    "Srisakdi": "Srisakdi",
    "SuperMarket": "SuperMarket",
}

MODE_THAI = "thai"
MODE_DOUBLE = "double"

SLOT_TR = "tr"
SLOT_EN = "en"

OFFSET_LIMIT = 100
WIDTH_RANGE = (50, 150)
SCALE_RANGE = (50, 250)
LAYOUT_BGS = ("photo1", "photo2", "gradient")


@dataclass
class InstallOptions:
    game_path: str = ""
    font: str = "CSPraKas"
    mode: str = MODE_THAI
    thai_first: bool = True
    color1: str = "#FFFFFF"
    color2: str = "#808080"
    size1: int = 28
    size2: int = 28
    speaker_colors: bool = True
    storybook: bool = True
    subtitle_style: bool = True
    # HUD offsets in percent of the screen from the game's layout, see gui/hud_layout_dialog.py
    sub_x: float = 0.0
    sub_y: float = 0.0
    sub_width: int = 100
    dialog_x: float = 0.0
    dialog_y: float = 0.0
    choice_x: float = 0.0
    choice_y: float = 0.0
    choice_scale: int = 100
    # background of the layout preview only, not used by the installer
    layout_bg: str = "photo1"
    # "don't show again" on the startup and install-finished notices
    hide_upgrade_notice: bool = False
    hide_done_notice: bool = False
    slot: str = SLOT_TR
    custom_sheets: list[dict] = field(default_factory=default_sheets)
    # default sheet keys (see core.custom.sheet_key) already offered; newer defaults get appended once
    known_default_sheets: list[str] = field(default_factory=lambda: [sheet_key(s) for s in default_sheets()])

    def validate(self) -> None:
        if not isinstance(self.custom_sheets, list) or any(
                not isinstance(s, dict) or not s.get("sheet_id") for s in self.custom_sheets):
            raise ValueError("invalid custom sheet list")
        if any(s.get("name_mode", "") not in NAME_MODES for s in self.custom_sheets):
            raise ValueError("invalid name mode")
        if not isinstance(self.known_default_sheets, list) or any(
                not isinstance(s, str) for s in self.known_default_sheets):
            raise ValueError("invalid known default sheet list")
        if self.font not in FONTS:
            raise ValueError(f"unknown font {self.font}")
        if self.mode not in (MODE_THAI, MODE_DOUBLE):
            raise ValueError(f"unknown mode {self.mode}")
        if self.slot not in (SLOT_TR, SLOT_EN):
            raise ValueError(f"unknown language slot {self.slot}")
        for c in (self.color1, self.color2):
            if len(c) != 7 or not c.startswith("#") or any(ch not in "0123456789abcdefABCDEF" for ch in c[1:]):
                raise ValueError(f"invalid colour {c}")
        for s in (self.size1, self.size2):
            if not 16 <= int(s) <= 48:
                raise ValueError(f"font size {s} out of range 16-48")
        for v in (self.sub_x, self.sub_y, self.dialog_x, self.dialog_y, self.choice_x, self.choice_y):
            if not isinstance(v, (int, float)) or not -OFFSET_LIMIT <= v <= OFFSET_LIMIT:
                raise ValueError(f"HUD offset {v} out of range -{OFFSET_LIMIT}-{OFFSET_LIMIT}")
        if not isinstance(self.hide_upgrade_notice, bool) or not isinstance(self.hide_done_notice, bool):
            raise ValueError("notice flags must be true/false")
        if self.layout_bg not in LAYOUT_BGS:
            raise ValueError(f"unknown layout background {self.layout_bg}")
        if not isinstance(self.sub_width, int) or not WIDTH_RANGE[0] <= self.sub_width <= WIDTH_RANGE[1]:
            raise ValueError(f"subtitle width {self.sub_width} out of range {WIDTH_RANGE[0]}-{WIDTH_RANGE[1]}")
        if not isinstance(self.choice_scale, int) or not SCALE_RANGE[0] <= self.choice_scale <= SCALE_RANGE[1]:
            raise ValueError(f"choice box scale {self.choice_scale} out of range {SCALE_RANGE[0]}-{SCALE_RANGE[1]}")


def settings_path():
    return app_data_dir() / "settings.json"


def _legacy_key(key: str) -> str:
    return f"{key}#{LEGACY_TABS[key]}" if key in LEGACY_TABS else key


def _add_new_default_sheets(opts: InstallOptions) -> None:
    for s in opts.custom_sheets:
        if not s.get("tab") and s["sheet_id"] in LEGACY_TABS:
            s["tab"] = LEGACY_TABS[s["sheet_id"]]
        if is_name_tab(s):
            if s.get("name") == s["tab"]:
                s["name"] = name_label(s["tab"])
            if not s.get("name_mode"):
                s["name_mode"] = NAME_DOUBLE
    have = {sheet_key(s) for s in opts.custom_sheets}
    known = {_legacy_key(k) for k in opts.known_default_sheets}
    for s in default_sheets():
        if sheet_key(s) not in known and sheet_key(s) not in have:
            opts.custom_sheets.append(s)
    opts.known_default_sheets = sorted(known | {sheet_key(s) for s in default_sheets()})


def load_options() -> InstallOptions:
    path = settings_path()
    opts = InstallOptions()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {f.name for f in fields(InstallOptions)}
            for k, v in data.items():
                if k in known:
                    setattr(opts, k, v)
            if "known_default_sheets" not in data:
                opts.known_default_sheets = [s.get("sheet_id") for s in opts.custom_sheets
                                             if isinstance(s, dict) and s.get("sheet_id")]
            opts.validate()
            _add_new_default_sheets(opts)
        except (OSError, ValueError, TypeError) as exc:
            log.warning("settings reset: %s", exc)
            opts = InstallOptions()
    return opts


def save_options(opts: InstallOptions) -> None:
    settings_path().write_text(json.dumps(asdict(opts), ensure_ascii=False, indent=2), encoding="utf-8")
