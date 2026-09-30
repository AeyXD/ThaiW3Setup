"""Re-apply the w3tu (svvv) subtitle patch on top of the game's current scripts.

The original mod shipped whole .ws files from game 4.0 which no longer match the
Remastered scripts. Here each change is expressed as an anchored edit, so it is
applied to whatever script version the user has, and fails loudly instead of
producing a script that does not compile.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MODULES_REL = Path("scripts/game/gui/hud/modules")

VARS_COLOR = """\
	// mod thai
	private var m_color1		: string;
	private var m_color2		: string;
	default m_color1 = "{color1}";
	default m_color2 = "{color2}";
"""

VARS_SIZE = """\
	private var m_size_default	: int;
	private var m_size1			: int;
	private var m_size2			: int;
	default m_size_default	 = 28;
	default m_size1	 = {size1};
	default m_size2	 = {size2};
"""

VARS_END = "\t// mod thai\n\n"

DIALOG_LINES = """\
		// mod thai
		text = StrReplaceAll(text, "  [", "</FONT><FONT size = '"+ IntToString( 27 + subtitleScale + (m_size2 - m_size_default) ) + "' COLOR='" + m_color2 + "'><br>[");
		text = "<FONT COLOR='" + m_color1 + "'>" + text + "</FONT>";
		// mod thai
"""

DIALOG_CHOICE = """\
			// mod thai
			if(StrContains(lastSetChoices[ i ].description, "  ["))
			{
				lastSetChoices[ i ].description = StrReplaceAll(lastSetChoices[ i ].description, "  [", " [");
			}
			// mod thai
"""

DIALOG_WITOLD = (
    '\t\t\ttext = "<FONT COLOR=\'#F8FF55\'>" + GetLocStringByKeyExt("Witold") + ": </FONT>'
    '<FONT COLOR=\'#5ACCF6\'>" + text + "</FONT>";\n'
)

ONELINER = """\
		// mod thai
		if(StrContains(value, "  ["))
		{
			value = StrReplaceAll(value, "  [", "</FONT><FONT COLOR='" + m_color2 + "'><br>[");
			value = "<FONT COLOR='" + m_color1 + "'>" + value + "</FONT>";
		}
		// mod thai

"""

QUEST_NAME = """\
		// mod thai
		if(StrContains(questName, "  ["))
		{
			questName = StrLeft(questName, StrFindFirst(questName, "  ["));
		}
		// mod thai

"""

QUEST_OBJECTIVE = """\
			// mod thai
			if(StrContains(objectiveName, "  "))
			{
				objectiveName = StrReplaceAll(objectiveName, "  ", " ");
			}
			// mod thai
"""

SUB_SPLIT = """\
		// mod thai
		htmlString = StrReplaceAll(htmlString, "  [", "</FONT><FONT size = '"+ IntToString( 27 + subScale + (m_size2 - m_size_default) ) + "' COLOR='" + m_color2 + "'><br>[");
		// mod thai
"""

SUB_SPEAKER = """\
			// mod thai
			if(speakerNameDisplayText == "Geralt")
				speakerNameDisplayText = "<FONT COLOR='#5ACCF7'>" + speakerNameDisplayText + "</FONT>";
			else if(speakerNameDisplayText == "Ciri")
				speakerNameDisplayText = "<FONT COLOR='#FC5593'>" + speakerNameDisplayText + "</FONT>";
			else if(speakerNameDisplayText != "" && speakerNameDisplayText != " ")
				speakerNameDisplayText = "<FONT COLOR='#F8FF56'>" + speakerNameDisplayText + "</FONT>";
			// mod thai
"""

SUB_WITOLD = (
    '\t\t\tspeakerNameDisplayText = "<FONT COLOR=\'#F8FF55\'>" + GetLocStringByKeyExt("Witold")  + ": </FONT>";\n'
)

SUB_COLOR = """\
		// mod thai
		htmlString = "<FONT COLOR='" + m_color1 + "'>" + htmlString + "</FONT>";
		// mod thai
"""

# "ScaleOnly" modules are never positioned by the engine, so the offset is applied
# on top of the position the flash module was laid out at (captured once).
PLACE_FN = """\
	// mod thai
	private var m_off_x			: float;
	private var m_off_y			: float;
	private var m_base_x		: float;
	private var m_base_y		: float;
	private var m_base_set		: bool;
	default m_off_x = {off_x};
	default m_off_y = {off_y};

	private function ModThaiPlace( flashModule : CScriptedFlashSprite )
	{{
		if ( !m_base_set )
		{{
			m_base_x = flashModule.GetX();
			m_base_y = flashModule.GetY();
			m_base_set = true;
		}}
		flashModule.SetX( m_base_x + curResolutionWidth * m_off_x / 100.0 );
		flashModule.SetY( m_base_y + curResolutionHeight * m_off_y / 100.0 );
	}}
	// mod thai

"""

PLACE_RETURN = """\
		// mod thai
		if ( super.UpdateScale( scale, flashModule ) )
		{
			ModThaiPlace( flashModule );
			return true;
		}
		ModThaiPlace( flashModule );
		return false;
		// mod thai
"""

SUB_WIDTH = """\
		// mod thai
		m_fxUpdateWidthSFF.InvokeSelfOneArg( FlashArgNumber( theGame.GetUIHorizontalFrameScale() * m_width_pct / 100.0 ) );
		// mod thai
"""

VARS_WIDTH = """\
	private var m_width_pct		: float;
	default m_width_pct = {width};
"""

# The dialogue line and the choice list are separate children of hud_dialog.redswf.
DIALOG_PLACE_FN = """\
	// mod thai
	private var m_line_x		: float;
	private var m_line_y		: float;
	private var m_choice_x		: float;
	private var m_choice_y		: float;
	private var m_line_bx		: float;
	private var m_line_by		: float;
	private var m_choice_bx		: float;
	private var m_choice_by		: float;
	private var m_choice_pct	: float;
	private var m_choice_bsx	: float;
	private var m_choice_bsy	: float;
	private var m_base_set		: bool;
	default m_line_x = {line_x};
	default m_line_y = {line_y};
	default m_choice_x = {choice_x};
	default m_choice_y = {choice_y};
	default m_choice_pct = {choice_scale};

	private function ModThaiPlace( flashModule : CScriptedFlashSprite )
	{{
		var line	: CScriptedFlashSprite;
		var choices	: CScriptedFlashSprite;

		line = flashModule.GetChildFlashSprite( "mcSubtitlesContainer" );
		choices = flashModule.GetChildFlashSprite( "mcOptionContainer" );
		if ( !line || !choices )
		{{
			return;
		}}
		if ( !m_base_set )
		{{
			m_line_bx = line.GetX();
			m_line_by = line.GetY();
			m_choice_bx = choices.GetX();
			m_choice_by = choices.GetY();
			m_choice_bsx = choices.GetXScale();
			m_choice_bsy = choices.GetYScale();
			m_base_set = true;
		}}
		line.SetX( m_line_bx + curResolutionWidth * m_line_x / 100.0 );
		line.SetY( m_line_by + curResolutionHeight * m_line_y / 100.0 );
		choices.SetX( m_choice_bx + curResolutionWidth * m_choice_x / 100.0 );
		choices.SetY( m_choice_by + curResolutionHeight * m_choice_y / 100.0 );
		choices.SetXScale( m_choice_bsx * m_choice_pct / 100.0 );
		choices.SetYScale( m_choice_bsy * m_choice_pct / 100.0 );
	}}

	protected function UpdateScale( scale : float, flashModule : CScriptedFlashSprite ) : bool
	{{
{place_return}	}}
	// mod thai

"""


def _num(value: float) -> str:
    return f"{float(value):.1f}"


class PatchError(Exception):
    pass


@dataclass
class Edit:
    kind: str            # "before", "after", "replace_line", "sub"
    anchor: str          # regex matched against each line (or whole text for "sub")
    text: str = ""
    count: int = 1       # exact number of matches expected; 0 means "at least one"
    optional: bool = False
    replacement: str = ""


@dataclass
class ScriptOptions:
    color1: str = "#FFFFFF"
    color2: str = "#808080"
    size1: int = 28
    size2: int = 28
    speaker_colors: bool = True
    # offsets in percent of the screen, relative to the game's own layout
    sub_x: float = 0.0
    sub_y: float = 0.0
    sub_width: int = 100
    dialog_x: float = 0.0
    dialog_y: float = 0.0
    choice_x: float = 0.0
    choice_y: float = 0.0
    choice_scale: int = 100


def _edits(name: str, o: ScriptOptions) -> list[Edit]:
    colors = VARS_COLOR.format(color1=o.color1, color2=o.color2)
    sizes = VARS_SIZE.format(size1=int(o.size1), size2=int(o.size2))
    if name == "hudModuleDialog.ws":
        edits = [
            Edit("before", r"^\s*protected var lastSetChoices\s*:", colors + sizes + VARS_END),
            Edit("before", r"^\s*private var subtitleScale\s*:\s*int;",
                 DIALOG_PLACE_FN.format(line_x=_num(o.dialog_x), line_y=_num(o.dialog_y),
                                        choice_x=_num(o.choice_x), choice_y=_num(o.choice_y),
                                        choice_scale=_num(o.choice_scale),
                                        place_return=PLACE_RETURN)),
            Edit("sub", r"IntToString\( 27 \+ subtitleScale \)",
                 replacement="IntToString( 27 + subtitleScale + (m_size1 - m_size_default) )", count=2),
            Edit("before", r"^\s*m_fxSentenceSetSFF\.InvokeSelfOneArg\( FlashArgString\( text \) \);", DIALOG_LINES),
            Edit("before", r"^\s*m_fxPreviousSentenceSetSFF\.InvokeSelfOneArg\( FlashArgString\( text \) \);", DIALOG_LINES),
            Edit("after", r"^\s*for \( i = 0; i < lastSetChoices\.Size\(\); i \+= 1 \)\s*$", "{\n" + DIALOG_CHOICE,
                 replacement="{"),
        ]
        if o.speaker_colors:
            edits.append(Edit("replace_line",
                              r'^\s*text = "<FONT COLOR=\'#5ACCF6\'>" \+ GetLocStringByKeyExt\("Witold"\) \+ ": " \+ text \+ "</FONT>";',
                              DIALOG_WITOLD, optional=True))
        return edits
    if name == "hudModuleOneliners.ws":
        return [
            Edit("before", r"^\s*private const var VISIBILITY_DISTANCE_SQUARED\s*:", colors + VARS_END),
            Edit("before", r"^\s*oneliner\.m_Target = \( CActor \)target;", ONELINER),
        ]
    if name == "hudModuleQuests.ws":
        return [
            Edit("before", r"^\s*questLevelsCount = theGame\.questLevelsContainer\.Size\(\);", QUEST_NAME),
            Edit("after", r"^\s*objectiveName = GetLocStringById\( data\.objectiveEntry\.GetTitleStringId\(\) \);", QUEST_OBJECTIVE),
        ]
    if name == "hudModuleSubtitles.ws":
        edits = [
            Edit("after", r"^\s*private var m_fxUpdateWidthSFF\s*:\s*CScriptedFlashFunction;",
                 "\n" + colors + sizes + VARS_WIDTH.format(width=_num(o.sub_width)) + VARS_END.rstrip("\n") + "\n"),
            Edit("before", r"^\s*protected function UpdateScale\(",
                 PLACE_FN.format(off_x=_num(o.sub_x), off_y=_num(o.sub_y))),
            Edit("replace_line",
                 r"^\s*m_fxUpdateWidthSFF\.InvokeSelfOneArg\( FlashArgNumber\( theGame\.GetUIHorizontalFrameScale\(\) \) \);",
                 SUB_WIDTH),
            Edit("replace_line", r"^\s*return super\.UpdateScale\( scale, flashModule \);", PLACE_RETURN),
            Edit("after", r"^\s*event\s+OnSubtitleAdded\(", "{\n" + SUB_SPLIT, replacement="{"),
            Edit("sub", r"IntToString\( 26 \+ subScale \)",
                 replacement="IntToString( 26 + subScale + (m_size1 - m_size_default) )", count=2),
            Edit("before", r"^\s*m_fxAddSubtitleSFF\.InvokeSelfThreeArgs\(", SUB_COLOR),
        ]
        if o.speaker_colors:
            edits.append(Edit("after", r'^\s*htmlString = ": "\s*\+ htmlString;', SUB_SPEAKER, optional=True))
            edits.append(Edit("replace_line",
                              r'^\s*speakerNameDisplayText = "<FONT COLOR=\'#5ACCF6\'>" \+ GetLocStringByKeyExt\("Witold"\)\s*\+ ": </FONT>";',
                              SUB_WITOLD, optional=True))
        return edits
    raise PatchError(f"no patch defined for {name}")


SCRIPT_FILES = ["hudModuleDialog.ws", "hudModuleOneliners.ws", "hudModuleQuests.ws", "hudModuleSubtitles.ws"]


def _detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def patch_text(name: str, source: str, opts: ScriptOptions) -> str:
    nl = _detect_newline(source)
    lines = source.replace("\r\n", "\n").split("\n")
    for edit in _edits(name, opts):
        if edit.kind == "sub":
            text = "\n".join(lines)
            new, n = re.subn(edit.anchor, edit.replacement, text)
            if (edit.count and n != edit.count) or n == 0:
                if edit.optional:
                    continue
                raise PatchError(f"{name}: expected {edit.count} matches for {edit.anchor!r}, found {n}")
            lines = new.split("\n")
            continue
        rx = re.compile(edit.anchor)
        hits = [i for i, line in enumerate(lines) if rx.search(line)]
        if (edit.count and len(hits) != edit.count) or not hits:
            if edit.optional:
                continue
            raise PatchError(f"{name}: expected {edit.count} matches for {edit.anchor!r}, found {len(hits)}")
        for i in reversed(hits):
            block = edit.text.rstrip("\n").split("\n")
            if edit.kind == "before":
                lines[i:i] = block
            elif edit.kind == "replace_line":
                lines[i:i + 1] = block
            elif edit.kind == "after":
                if edit.replacement:
                    # The anchor is followed by an opening brace line that the block re-creates.
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j >= len(lines) or lines[j].strip() != edit.replacement:
                        raise PatchError(f"{name}: expected '{edit.replacement}' after {edit.anchor!r}")
                    indent = lines[j][: len(lines[j]) - len(lines[j].lstrip())]
                    block[0] = indent + block[0].strip()
                    lines[i + 1:j + 1] = block
                else:
                    lines[i + 1:i + 1] = block
    return nl.join(lines)


def build_scripts(game_scripts_modules: Path, opts: ScriptOptions) -> dict[str, bytes]:
    """Return {file name: patched bytes}. Raises PatchError if any file cannot be patched."""
    out = {}
    for name in SCRIPT_FILES:
        src_path = game_scripts_modules / name
        if not src_path.exists():
            raise PatchError(f"ไม่พบไฟล์ script ของเกม: {src_path}")
        raw = src_path.read_bytes()
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            text, enc = raw.decode("utf-16"), "utf-16"
        else:
            text, enc = raw.decode("latin-1"), "latin-1"
        patched = patch_text(name, text, opts)
        out[name] = patched.encode(enc)
    return out
