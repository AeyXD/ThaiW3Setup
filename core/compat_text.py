"""Thai for the text a UI mod keeps in its own ActionScript instead of the game's .w3strings.

Ink and Iron builds its labels from rows like {EN: "Hide card", PL: "Ukryj kartę", ...} and picks the entry
for the game's language. Thai sits in the en or tr language slot, so both entries of a row get the Thai text.
A row is found in the bytecode as `pushstring "EN"` followed by `pushstring <text>`. The code also uses some of
those English strings as keys, so the Thai goes to the end of the constant pool and only the row's pushstring
is pointed at it, its operand padded to its old width so no code moves.
"""
from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from .abc_patch import DO_ABC, _u30, string_pool
from .text_builder import guard_trailing_mark
from .thai_wrap import ThaiWrapper, load_words

log = logging.getLogger(__name__)

OP_PUSHSTRING = 0x2C
LOC_CODES = ("EN", "TR")

INK_AND_IRON: dict[str, str] = {
    # alchemy, crafting
    "Lv {0}": "เลเวล {0}",
    "Ready to craft": "พร้อมสร้าง",
    # blacksmith
    "Maximum sockets": "ช่องใส่รูนเต็มแล้ว",
    "New socket": "ช่องใส่รูนใหม่",
    # character: skill tree and mutagens
    "Equip a mutagen to add a group bonus": "ใส่สารกลายพันธุ์เพื่อรับโบนัสกลุ่ม",
    "No mutagen": "ไม่มีสารกลายพันธุ์",
    "Mutagen slot locked": "ช่องสารกลายพันธุ์ล็อคอยู่",
    "Unlocks at {0} skill points earned": "ปลดล็อคเมื่อได้แต้มทักษะครบ {0} แต้ม",
    "Available": "ใช้ได้",
    "Equipped": "สวมใส่แล้ว",
    "Group {0}, slot {1}": "กลุ่ม {0} ช่อง {1}",
    "In the tree": "ในสายทักษะ",
    "Leads to  {0}": "นำไปสู่  {0}",
    "Learned": "เรียนแล้ว",
    "Locked": "ล็อคอยู่",
    "Mutagens held": "สารกลายพันธุ์ที่มี",
    "No mutagen in this group.": "กลุ่มนี้ไม่มีสารกลายพันธุ์",
    "The group mutagen is another colour: no synergy with this skill. Bonus {0}":
        "สารกลายพันธุ์ของกลุ่มเป็นคนละสี ไม่เสริมกับทักษะนี้ โบนัส {0}",
    "Not equipped": "ยังไม่ได้สวมใส่",
    "Not learned yet": "ยังไม่ได้เรียน",
    "Requires  {0}": "ต้องมี  {0}",
    "Select a skill in the tree to read what it does.": "เลือกทักษะในสายทักษะเพื่ออ่านว่าทำอะไรได้",
    "Mutagen synergy: this skill raises the group bonus. Now {0}":
        "สารกลายพันธุ์เสริมกัน ทักษะนี้เพิ่มโบนัสกลุ่ม ตอนนี้ {0}",
    # dialogue choices
    "Armorer": "ช่างทำชุดเกราะ",
    "Auction": "ประมูล",
    "Axii": "Axii",
    "Back": "กลับ",
    "Bribe": "ติดสินบน",
    "Contract": "สัญญาจ้าง",
    "Craftsman": "ช่างฝีมือ",
    "Dice poker": "โป๊กเกอร์ลูกเต๋า",
    "Drinking": "ดื่ม",
    "Fistfight": "ดวลหมัด",
    "Gift": "ของขวัญ",
    "Gwent": "Gwent",
    "Barber": "ช่างตัดผม",
    "House": "บ้าน",
    "Knife throwing": "ปามีด",
    "Leave": "จากไป",
    "Persuade": "โน้มน้าว",
    "Runewright": "Runewright",
    "Shave": "โกนหนวด",
    "Blacksmith": "ช่างตีเหล็ก",
    "Stash": "กล่องเก็บของ",
    "Teacher": "ครู",
    "Shop": "ร้านขายของ",
    "Fast Travel": "เดินทางเร็ว",
    "Wager": "พนัน",
    "Arm wrestling": "งัดข้อ",
    # inventory
    "Inventory": "ช่องเก็บของ",
    "Select an item to preview": "เลือกไอเท็มเพื่อดูตัวอย่าง",
    "The items that fit it open right beside it.": "ไอเท็มที่ใส่ได้จะเปิดขึ้นข้างๆ",
    "Choose a slot": "เลือกช่อง",
    "Compare": "เปรียบเทียบ",
    "{0} fit": "ใส่ได้ {0}",
    "Nothing in your bag fits here.": "ไม่มีของในกระเป๋าที่ใส่ช่องนี้ได้",
    "Satchel": "ย่าม",
    "Items that fit no slot": "ไอเท็มที่ไม่มีช่องใส่",
    "{0} more": "อีก {0}",
    # pause menu
    "Hide background": "ซ่อนพื้นหลัง",
    "Show background": "แสดงพื้นหลัง",
    "Sections": "หมวด",
    "Jump to day": "ไปยังวัน",
    "New save": "เซฟใหม่",
    "It will be replaced by the current game.": "เซฟนี้จะถูกแทนที่ด้วยเกมปัจจุบัน",
    "Overwrite this save?": "บันทึกทับเซฟนี้หรือไม่?",
    "Overwrite": "บันทึกทับ",
    "Paused": "หยุดชั่วคราว",
    # meditation clock
    "Dawn": "รุ่งสาง",
    "Dusk": "พลบค่ำ",
    "Midnight": "เที่ยงคืน",
    "Noon": "เที่ยงวัน",
    # loot
    "Hide card": "ซ่อนการ์ด",
    "Show card": "แสดงการ์ด",
    "Quest": "เควส",
}


# the main menu's title, drawn as text where the game has its logo; Thai only with the Thai logo option
INK_AND_IRON_TITLE: dict[str, str] = {
    "THE WITCHER": "เดอะ วิทเชอร์",
    "WILD HUNT": "ไวลด์ ฮันท์",
}

# Option.iaiDecor lays out iaiMark (the action suffix next to a dialogue choice) as
#   y = tfLine.y + 2 + … + (lineHeight - mark.height) * factor
# Ink and Iron ships factor 0.6 (double pool index 19). Thai glyphs sit optically low at
# that value; 0.5 (index 4) is geometric vertical center. Only the subtract/pushdouble/
# multiply/add site is rewritten — the same 0.6 constant is also used for unread alpha.
MARK_Y_FACTOR_FROM = 19  # 0.6
MARK_Y_FACTOR_TO = 4     # 0.5
# subtract, pushdouble <idx>, multiply, add
_MARK_Y_PREFIX = bytes([0xA1, 0x2F])
_MARK_Y_SUFFIX = bytes([0xA2, 0xA0])


@lru_cache(maxsize=1)
def _wrapper() -> ThaiWrapper:
    return ThaiWrapper(load_words())


def prepare(text: str) -> str:
    """Thai as the game's own strings carry it: word breaks for wrapping, no tone mark at the very end."""
    return guard_trailing_mark(_wrapper().wrap(text))


def _u30_bytes(v: int, width: int = 0) -> bytes:
    """u30 encoding; width pads it with continuation bytes, which AVM2 reads the same."""
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b)
        if not v and len(out) >= width:
            break
        out[-1] |= 0x80
    return bytes(out)


def _pushes(d: bytes, idx: int, start: int) -> list[int]:
    """Offsets of `pushstring idx` from start on; random bytes can look like one too."""
    needle = bytes([OP_PUSHSTRING]) + _u30_bytes(idx)
    found, p = [], d.find(needle, start)
    while p >= 0:
        found.append(p)
        p = d.find(needle, p + 1)
    return found


@dataclass
class _Entry:
    code: str
    value: int    # string index
    operand: int  # offset of the value's u30 operand
    width: int


def _loc_rows(d: bytes, strings: list[str], code_start: int) -> list[list[_Entry]]:
    """Each row's entries for LOC_CODES, in code order; a row starts at its EN entry."""
    events = []
    for code_idx, code in ((i, s) for i, s in enumerate(strings) if s in LOC_CODES):
        for p in _pushes(d, code_idx, code_start):
            try:
                q = _u30(d, p + 1)[1]
                if d[q] == OP_PUSHSTRING:
                    value, end = _u30(d, q + 1)
                    if 0 < value < len(strings):
                        events.append(_Entry(code, value, q + 1, end - q - 1))
            except IndexError:
                continue
    rows: list[list[_Entry]] = []
    for e in sorted(events, key=lambda e: e.operand):
        if e.code == LOC_CODES[0] or not rows:
            rows.append([])
        rows[-1].append(e)
    return rows


def _zero_draw_letter_spacing(abc: bytearray, code_start: int) -> int:
    """Zero Ink and Iron's text-draw letterSpacing (last of 9 args: pushbyte before call* argc=9).

    Latin UI uses 1–12 so caps track wide; the same values leave Thai looking broken across menus,
    meditation labels, and nav tabs — not only the logo titles.
    """
    patched = 0
    j = code_start
    while j < len(abc) - 4:
        if abc[j] == 0x24 and abc[j + 2] in (0x46, 0x4F):  # pushbyte + callproperty/callpropvoid
            try:
                _, q = _u30(abc, j + 3)
            except (IndexError, struct.error):
                j += 1
                continue
            if q < len(abc) and abc[q] == 9 and abc[j + 1] != 0:
                abc[j + 1] = 0
                patched += 1
                j = q + 1
                continue
        j += 1
    return patched


def _read_bits(data: bytes | bytearray, bit_pos: int, n: int) -> tuple[int, int]:
    v = 0
    for _ in range(n):
        byte = data[bit_pos >> 3]
        bit = 7 - (bit_pos & 7)
        v = (v << 1) | ((byte >> bit) & 1)
        bit_pos += 1
    return v, bit_pos


def _read_sbits(data: bytes | bytearray, bit_pos: int, n: int) -> tuple[int, int]:
    v, bit_pos = _read_bits(data, bit_pos, n)
    if n and (v & (1 << (n - 1))):
        v -= 1 << n
    return v, bit_pos


def _sbits_needed(v: int) -> int:
    """Smallest SWF SB field width that can hold v."""
    n = 1
    while not (-(1 << (n - 1)) <= v < (1 << (n - 1))):
        n += 1
    return n


def _write_bits(data: bytearray, bit_pos: int, n: int, value: int) -> int:
    u = value & ((1 << n) - 1) if n else 0
    for i in range(n - 1, -1, -1):
        byte_i = bit_pos >> 3
        while byte_i >= len(data):
            data.append(0)
        b = 7 - (bit_pos & 7)
        if (u >> i) & 1:
            data[byte_i] |= 1 << b
        else:
            data[byte_i] &= ~(1 << b)
        bit_pos += 1
    return bit_pos


def _parse_place_matrix(place: bytes | bytearray) -> tuple[int, int, int, int, int] | None:
    """(matrix_bit_start, nbits_at, tx, ty, matrix_end_bit) or None if no matrix."""
    flags = place[0]
    if not (flags & 0x04):
        return None
    p = 3 + (2 if flags & 0x02 else 0)
    bit = p * 8
    has_scale, bit = _read_bits(place, bit, 1)
    if has_scale:
        n, bit = _read_bits(place, bit, 5)
        _, bit = _read_sbits(place, bit, n)
        _, bit = _read_sbits(place, bit, n)
    has_rotate, bit = _read_bits(place, bit, 1)
    if has_rotate:
        n, bit = _read_bits(place, bit, 5)
        _, bit = _read_sbits(place, bit, n)
        _, bit = _read_sbits(place, bit, n)
    nbits_at = bit
    nbits, bit = _read_bits(place, bit, 5)
    tx, bit = _read_sbits(place, bit, nbits)
    ty, bit = _read_sbits(place, bit, nbits)
    return p * 8, nbits_at, tx, ty, bit


def _bump_place_matrix(place: bytearray, dtx: int = 0, dty: int = 0) -> bytearray | None:
    """Add dtx/dty (twips) to a PlaceObject2 matrix. Grows the tag if nbits must widen."""
    parsed = _parse_place_matrix(place)
    if parsed is None:
        return None
    _matrix_start, nbits_at, tx, ty, matrix_end = parsed
    new_tx, new_ty = tx + dtx, ty + dty
    old_nbits, _ = _read_bits(place, nbits_at, 5)
    limit = 1 << (old_nbits - 1)
    if -limit <= new_tx < limit and -limit <= new_ty < limit:
        out = bytearray(place)
        bit = nbits_at
        bit = _write_bits(out, bit, 5, old_nbits)
        bit = _write_bits(out, bit, old_nbits, new_tx)
        _write_bits(out, bit, old_nbits, new_ty)
        return out
    # values need a wider SB field — rebuild matrix and keep trailing fields
    need = max(_sbits_needed(new_tx), _sbits_needed(new_ty), 1)
    old_after = (matrix_end + 7) // 8
    if nbits_at & 7:
        out = bytearray(place[: (nbits_at >> 3) + 1])
        out[-1] &= (0xFF << (8 - (nbits_at & 7))) & 0xFF
    else:
        out = bytearray(place[: nbits_at >> 3])
    bit = nbits_at
    bit = _write_bits(out, bit, 5, need)
    bit = _write_bits(out, bit, need, new_tx)
    bit = _write_bits(out, bit, need, new_ty)
    if bit & 7:
        bit = _write_bits(out, bit, 8 - (bit & 7), 0)
    return out[: bit >> 3] + bytearray(place[old_after:])


def _encode_tag(tag: int, payload: bytes) -> bytes:
    if len(payload) < 0x3F:
        return struct.pack("<H", (tag << 6) | len(payload)) + payload
    return struct.pack("<HI", (tag << 6) | 0x3F, len(payload)) + payload


def shift_game_version(body: bytes, dtx_twips: int = 2400, dty_twips: int = 0) -> bytes | None:
    """Nudge txtVersion PlaceObject2 right so the game version clears the wider Thai logo title.

    mcModVersion lives in VerificationModPreview (mod list), not the menu logo — do not move it.
    """
    moved = 0
    needle = b"txtVersion\0"

    def walk(data: bytes, root: bool) -> bytearray:
        nonlocal moved
        if root:
            nbits = data[0] >> 3
            p = (5 + 4 * nbits + 7) // 8 + 4
            out = bytearray(data[:p])
        else:
            p = 0
            out = bytearray()
        while p + 2 <= len(data):
            code_len = struct.unpack_from("<H", data, p)[0]
            tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
            if ln == 0x3F:
                ln = struct.unpack_from("<I", data, hp)[0]
                hp += 4
            payload = data[hp:hp + ln]
            if tag == 39 and len(payload) >= 4:  # DefineSprite — nested tags after id+frames
                nested = walk(payload[4:], False)
                out += _encode_tag(tag, payload[:4] + bytes(nested))
            elif tag == 26 and needle in payload:
                bumped = _bump_place_matrix(bytearray(payload), dtx_twips, dty_twips)
                if bumped is not None:
                    out += _encode_tag(tag, bytes(bumped))
                    moved += 1
                else:
                    out += data[p:hp + ln]
            else:
                out += data[p:hp + ln]
            p = hp + ln
            if tag == 0:
                break
        out += data[p:]
        return out

    result = walk(body, True)
    if not moved:
        return None
    log.info("shifted txtVersion by (%d,%d) twips at %d place(s)", dtx_twips, dty_twips, moved)
    return bytes(result)


# old name kept for callers/tests that still import it
shift_mc_mod_version = shift_game_version


# Ink and Iron Gwent HUD: Thai (and Sarabun Latin) sits optically high/low in the parchment bars
# and score banners. Nudge PlaceObject2 matrices; SymbolClass names identify the player sprites.
GWENT_OPPONENT_NAME_DTY = 200   # PlayerRendererOpponent txtPlayerName / txtFactionName — down
GWENT_PLAYER_NAME_DTY = -200    # PlayerRenderer — up
GWENT_SCORE_DTY = -140          # txtScore in name-bar and board-row banners — up toward center
_GWENT_NAME_INSTANCES = (b"txtPlayerName\0", b"txtFactionName\0")
_GWENT_SCORE_INSTANCE = b"txtScore\0"


def _symbol_classes(body: bytes) -> dict[int, str]:
    """Character id -> SymbolClass name for the root timeline."""
    nbits = body[0] >> 3
    p = (5 + 4 * nbits + 7) // 8 + 4
    out: dict[int, str] = {}
    while p + 2 <= len(body):
        code_len = struct.unpack_from("<H", body, p)[0]
        tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, hp)[0]
            hp += 4
        if tag == 76 and ln >= 2:  # SymbolClass
            n = struct.unpack_from("<H", body, hp)[0]
            q = hp + 2
            for _ in range(n):
                if q + 2 > hp + ln:
                    break
                cid = struct.unpack_from("<H", body, q)[0]
                q += 2
                z = body.find(b"\0", q, hp + ln)
                if z < 0:
                    break
                out[cid] = body[q:z].decode("utf-8", "replace")
                q = z + 1
        p = hp + ln
        if tag == 0:
            break
    return out


def _gwent_place_dty(sprite_name: str, payload: bytes) -> int | None:
    """Vertical nudge (twips) for one PlaceObject2 payload, or None to leave it."""
    if _GWENT_SCORE_INSTANCE in payload:
        return GWENT_SCORE_DTY
    if not any(n in payload for n in _GWENT_NAME_INSTANCES):
        return None
    short = sprite_name.rsplit(".", 1)[-1]
    if short == "PlayerRendererOpponent":
        return GWENT_OPPONENT_NAME_DTY
    if short == "PlayerRenderer":
        return GWENT_PLAYER_NAME_DTY
    return None


def align_gwent_hud(body: bytes) -> bytes | None:
    """Nudge Gwent player names and center score digits in Ink and Iron's gwint_game HUD."""
    symbols = _symbol_classes(body)
    if not any(n.rsplit(".", 1)[-1] in ("PlayerRenderer", "PlayerRendererOpponent") for n in symbols.values()):
        return None
    moved = 0

    def walk(data: bytes, root: bool, sprite_id: int | None = None) -> bytearray:
        nonlocal moved
        if root:
            nbits = data[0] >> 3
            p = (5 + 4 * nbits + 7) // 8 + 4
            out = bytearray(data[:p])
        else:
            p = 0
            out = bytearray()
        sprite_name = symbols.get(sprite_id, "") if sprite_id is not None else ""
        while p + 2 <= len(data):
            code_len = struct.unpack_from("<H", data, p)[0]
            tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
            if ln == 0x3F:
                ln = struct.unpack_from("<I", data, hp)[0]
                hp += 4
            payload = data[hp:hp + ln]
            if tag == 39 and len(payload) >= 4:  # DefineSprite
                sid = struct.unpack_from("<H", payload, 0)[0]
                nested = walk(payload[4:], False, sid)
                out += _encode_tag(tag, payload[:4] + bytes(nested))
            elif tag == 26:
                dty = _gwent_place_dty(sprite_name, payload)
                if dty is not None:
                    bumped = _bump_place_matrix(bytearray(payload), 0, dty)
                    if bumped is not None:
                        out += _encode_tag(tag, bytes(bumped))
                        moved += 1
                    else:
                        out += data[p:hp + ln]
                else:
                    out += data[p:hp + ln]
            else:
                out += data[p:hp + ln]
            p = hp + ln
            if tag == 0:
                break
        out += data[p:]
        return out

    result = walk(body, True)
    if not moved:
        return None
    log.info("aligned gwent HUD at %d place(s)", moved)
    return bytes(result)


def translate_abc(d: bytes, table: dict[str, str], plain: dict[str, str] | None = None) -> tuple[bytes, int] | None:
    """A DoABC tag body with the rows' text from table in Thai, and how many strings changed.
    plain replaces whole strings in the pool, for text outside any row that the code only shows
    (menu logo titles: no word-break hair spaces)."""
    abc = d.index(b"\0", 4) + 1
    pool_start, spans, pool_end = string_pool(d, abc)
    strings = [""] + [d[a:b].decode("utf-8", "replace") for a, b in spans]
    # logo titles stay as written — wrap/prepare would insert hair spaces between Thai clusters
    replaced = {i: plain[s] for i, s in enumerate(strings) if plain and s in plain}
    if not replaced and not any(s in LOC_CODES for s in strings):
        return None
    added: dict[str, int] = {}
    repoint: list[tuple[_Entry, int]] = []
    for row in _loc_rows(d, strings, pool_end) if table else []:
        en = next((e for e in row if e.code == LOC_CODES[0]), None)
        thai = table.get(strings[en.value]) if en else None
        if thai is None:
            continue
        thai = prepare(thai)
        idx = added.setdefault(thai, len(strings) + len(added))
        for e in row:
            if idx >= 1 << (7 * e.width):
                log.info("kept %r: no room for a larger string index", strings[e.value])
            elif strings[e.value] != thai:
                repoint.append((e, idx))
    if not repoint and not replaced:
        return None
    pool = bytearray(_u30_bytes(len(strings) + len(added)))
    for i, (a, b) in enumerate(spans, start=1):
        raw = replaced[i].encode("utf-8") if i in replaced else d[a:b]
        pool += _u30_bytes(len(raw)) + raw
    for thai in added:
        raw = thai.encode("utf-8")
        pool += _u30_bytes(len(raw)) + raw
    out = bytearray(d[:pool_start] + bytes(pool) + d[pool_end:])
    shift = len(pool) - (pool_end - pool_start)
    for e, idx in repoint:
        out[e.operand + shift:e.operand + shift + e.width] = _u30_bytes(idx, e.width)
    n = _zero_draw_letter_spacing(out, pool_start + len(pool))
    if n:
        log.info("zeroed draw letterSpacing at %d site(s)", n)
    return bytes(out), len(repoint) + len(replaced)


def _mark_y_factor_sites(body: bytes | bytearray, factor_idx: int) -> list[int]:
    """Offsets of the pushdouble operand in Option.iaiDecor's iaiMark Y formula."""
    needle = _MARK_Y_PREFIX + _u30_bytes(factor_idx) + _MARK_Y_SUFFIX
    found, p = [], 0
    while True:
        p = body.find(needle, p)
        if p < 0:
            return found
        found.append(p + 2)  # operand of pushdouble
        p += 1


def align_dialog_action_mark(body: bytes) -> bytes | None:
    """Center Ink and Iron's dialogue-option action suffix (iaiMark) on the option line."""
    nbits = body[0] >> 3
    p = (5 + 4 * nbits + 7) // 8 + 4
    out = [body[:p]]
    changed = 0
    while p + 2 <= len(body):
        code_len = struct.unpack_from("<H", body, p)[0]
        tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, hp)[0]
            hp += 4
        if tag == DO_ABC:
            chunk = bytearray(body[hp:hp + ln])
            sites = _mark_y_factor_sites(chunk, MARK_Y_FACTOR_FROM)
            for op in sites:
                chunk[op:op + 1] = _u30_bytes(MARK_Y_FACTOR_TO)
                changed += 1
            if sites:
                out.append(struct.pack("<HI", (tag << 6) | 0x3F, len(chunk)) + bytes(chunk))
            else:
                out.append(body[p:hp + ln])
        else:
            out.append(body[p:hp + ln])
        p = hp + ln
        if tag == 0:
            break
    if not changed:
        return None
    log.info("centered dialog action mark at %d site(s)", changed)
    out.append(body[p:])
    return b"".join(out)


def translate_swf(body: bytes, table: dict[str, str], plain: dict[str, str] | None = None) -> bytes | None:
    """An uncompressed SWF body (after the 8-byte header) with its ActionScript labels in Thai
    and Ink and Iron draw letterSpacing zeroed."""
    nbits = body[0] >> 3
    p = (5 + 4 * nbits + 7) // 8 + 4
    out = [body[:p]]
    changed = 0
    while p + 2 <= len(body):
        code_len = struct.unpack_from("<H", body, p)[0]
        tag, ln, hp = code_len >> 6, code_len & 0x3F, p + 2
        if ln == 0x3F:
            ln = struct.unpack_from("<I", body, hp)[0]
            hp += 4
        done = translate_abc(body[hp:hp + ln], table, plain) if tag == DO_ABC else None
        if done is not None:
            out.append(struct.pack("<HI", (tag << 6) | 0x3F, len(done[0])) + done[0])
            changed += done[1]
        elif tag == DO_ABC:
            chunk = bytearray(body[hp:hp + ln])
            try:
                abc = chunk.index(b"\0", 4) + 1
                _, _, pool_end = string_pool(chunk, abc)
                n = _zero_draw_letter_spacing(chunk, pool_end)
            except (ValueError, struct.error, IndexError):
                n = 0
            if n:
                out.append(struct.pack("<HI", (tag << 6) | 0x3F, len(chunk)) + bytes(chunk))
                changed += n
            else:
                out.append(body[p:hp + ln])
        else:
            out.append(body[p:hp + ln])
        p = hp + ln
        if tag == 0:
            break
    if not changed:
        return None
    out.append(body[p:])
    return b"".join(out)


def translator(table: dict[str, str], plain: dict[str, str] | None = None) -> Callable[[bytes], bytes | None]:
    def apply(body: bytes) -> bytes | None:
        translated = translate_swf(body, table, plain)
        base = translated if translated is not None else body
        changed = translated is not None
        # game version (txtVersion) sits where the English logo ended; nudge right for Thai titles
        if plain:
            shifted = shift_game_version(base)
            if shifted is not None:
                base = shifted
                changed = True
        for align in (align_dialog_action_mark, align_gwent_hud):
            out = align(base)
            if out is not None:
                base = out
                changed = True
        return base if changed else None
    return apply
