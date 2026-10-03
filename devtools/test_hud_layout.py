"""HUD position patch and option checks (needs the game scripts)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gamepath import GAME
from dataclasses import replace
from pathlib import Path

from core.options import InstallOptions
from core.script_patcher import ScriptOptions, build_scripts
from gui.hud_layout_dialog import clamp_offset

MODULES = Path(GAME) / "content/content0/scripts/game/gui/hud/modules"


def scripts(**kw) -> dict[str, str]:
    return {k: v.decode("latin-1") for k, v in build_scripts(MODULES, ScriptOptions(**kw)).items()}


def test_default_patch():
    out = scripts()
    sub, dlg = out["hudModuleSubtitles.ws"], out["hudModuleDialog.ws"]
    assert "default m_off_x = 0.0;" in sub and "default m_width_pct = 100.0;" in sub
    assert "* m_width_pct / 100.0" in sub
    assert "FlashArgNumber( theGame.GetUIHorizontalFrameScale() ) )" not in sub
    assert "return super.UpdateScale" not in sub
    assert sub.count("ModThaiPlace( flashModule );") == 2
    assert dlg.count("protected function UpdateScale(") == 1
    assert dlg.count("private function ModThaiPlace(") == 1
    assert '"mcSubtitlesContainer"' in dlg and '"mcOptionContainer"' in dlg
    assert "default m_line_x = 0.0;" in dlg and "default m_choice_y = 0.0;" in dlg
    assert "default m_choice_pct = 100.0;" in dlg
    assert "choices.SetXScale( m_choice_bsx * m_choice_pct / 100.0 );" in dlg


def test_moved_patch():
    out = scripts(sub_x=-5, sub_y=-12.5, sub_width=120, dialog_x=3, dialog_y=-8, choice_x=-20, choice_y=10,
                  choice_scale=130)
    sub, dlg = out["hudModuleSubtitles.ws"], out["hudModuleDialog.ws"]
    assert "default m_choice_pct = 130.0;" in dlg
    assert "default m_off_x = -5.0;" in sub and "default m_off_y = -12.5;" in sub
    assert "default m_width_pct = 120.0;" in sub
    assert "default m_line_x = 3.0;" in dlg and "default m_line_y = -8.0;" in dlg
    assert "default m_choice_x = -20.0;" in dlg and "default m_choice_y = 10.0;" in dlg
    # each class keeps balanced braces
    for text in (sub, dlg):
        assert text.count("{") == text.count("}")


def test_validate():
    InstallOptions(sub_x=100, sub_y=-100, sub_width=150, dialog_x=12.5, choice_x=-75, choice_scale=250).validate()
    for bad in (dict(sub_x=100.5), dict(dialog_y=-110), dict(choice_x=101), dict(layout_bg="nope"), dict(sub_width=40), dict(sub_width=12.5), dict(sub_x="1"),
                dict(choice_scale=45), dict(choice_scale=255), dict(choice_scale=100.5)):
        try:
            replace(InstallOptions(), **bad).validate()
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad}")


def test_clamp():
    assert clamp_offset(100, 50, 400, 0) == 0
    assert clamp_offset(0, 10, 10000, 150) == 100       # capped by OFFSET_LIMIT
    assert clamp_offset(300, 50, 400, 50) == 12.5       # right edge at 350 -> 400
    assert clamp_offset(100, 50, 400, -40) == -25       # left edge at 0
    assert clamp_offset(100, 50, 400, 3.3) == 3.5       # 0.5 steps


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
