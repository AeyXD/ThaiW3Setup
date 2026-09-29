from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields

from .custom import default_sheets
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
    slot: str = SLOT_TR
    custom_sheets: list[dict] = field(default_factory=default_sheets)

    def validate(self) -> None:
        if not isinstance(self.custom_sheets, list) or any(
                not isinstance(s, dict) or not s.get("sheet_id") for s in self.custom_sheets):
            raise ValueError("invalid custom sheet list")
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


def settings_path():
    return app_data_dir() / "settings.json"


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
            opts.validate()
        except (OSError, ValueError, TypeError) as exc:
            log.warning("settings reset: %s", exc)
            opts = InstallOptions()
    return opts


def save_options(opts: InstallOptions) -> None:
    settings_path().write_text(json.dumps(asdict(opts), ensure_ascii=False, indent=2), encoding="utf-8")
