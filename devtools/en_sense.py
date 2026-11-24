"""ใช้ภาษาอังกฤษต้นฉบับช่วยตัดข้อเสนอของ find_wrong_word / find_ral_swaps ที่จับผิด

คู่สับสนพวกนี้เป็นคำจริงทั้งคู่ (ขา/ข้า, เข่า/เขา, รุก/ลุก) บริบทไทยอย่างเดียวจึงตัดสินไม่ได้
แต่ต้นฉบับบอกความหมายได้ชัด: "wherever our legs carry us" → ขา ถูก

หลักตัดสิน (ใช้เมื่อมีภาษาอังกฤษของข้อความนั้นเท่านั้น):
1. ความหมายของ**คำเดิม**ปรากฏในอังกฤษ → คำเดิมถูก ไม่ต้องเสนอ
2. ความหมายของ**คำที่เสนอ**ไม่ปรากฏในอังกฤษเลย → ไม่มีหลักฐานให้เปลี่ยน ไม่ต้องเสนอ

คำที่ไม่มีใน SENSES ไม่ถูกตัด (ปล่อยให้คนตรวจตามเดิม) — เพิ่มคำได้เมื่อพบผลจับผิดซ้ำ
คำที่ไม่ผูกกับคำอังกฤษใดชัด ๆ (ข้า, ไอ้, ที่, คำลงท้าย) อย่าใส่ เพราะข้อ 2 จะซ่อนคำผิดจริง
ที่มาของรายการ: ตรวจ wrong_word.csv 219 จุด + ral_swaps.csv 48 จุด ทีละจุด (2026-11-24)
"""
from __future__ import annotations

import re

SENSES = {
    # wrong_word: คำเดิมที่ถูก (ข้อ 1)
    "ขา": r"legs?|foot|feet|footwork|knees?",
    "เข่า": r"knees?",
    "รู": r"holes?|cranny|burrow|bunghole",
    "ตั๋ว": r"tickets?",
    "ท้อง": r"bell(y|ies)|stomach|gut",
    "แท้ง": r"miscarr|child inside|sapped",
    "สั่น": r"trembl|shak|quiver|shiver",
    "ค้น": r"search|rummag|examin",
    "คุ้ย": r"rummag|dig|examin|scour|acorn",
    "ซ้อม": r"beat|rehears|practi|drill",
    "ข้าว": r"grain|rice|food|mouths?|bread",
    "ไอ": r"cough|vapou?r|steam|fume",
    "สิง": r"possess|inhabit",
    "ป้า": r"aunt",
    "ล่อง": r"sail|float|drift",
    "บิ่น": r"chipped",
    "อาน": r"saddle",
    "หม้อ": r"pots?\b|cauldron",
    "ผา": r"cliff|crag|bluff",
    "ผ่า": r"cut|slice|split|incision",
    "บ่น": r"nag|complain|grumbl|whin|curs",
    "สร่าง": r"sober",
    "ต้น": r"trees?|willow|stalk|oak|plant",
    "สู้": r"fight|bout|battle|duel|combat",
    "ร่าย": r"curse|spell|utter|incant",
    "ร้าย": r"terrible|wicked|evil|vicious",
    "ลา": r"farewell|goodbye|leave|resign|gave up",
    "ห่าน": r"goose|geese",
    "ยื่น": r"file|submit|hand|offer",
    "ย้าย": r"move|moved|transfer|relocat|pack",
    "ส่อง": r"watch|peek|peep|look",
    "ขว้าง": r"throw|hurl|toss",
    "หลั่ง": r"spil|shed",
    "ชา": r"numb",
    "แก่": r"old|elder|age",
    "ยั้ง": r"restrain|resist|hold back|refrain",
    "กลั้ว": r"rins|gargl|wash",
    "เสียง": r"voice|sound|noise",
    "คาง": r"chin",
    "รอย": r"wounds?|marks?|traces?|tracks?",
    "หมู": r"pigs?|hogs?|boar|swine",
    "ปา": r"throw",
    "ท่า": r"stance|pose|horseback|position",
    "ทา": r"smear|rub|apply",
    "มั่น": r"sure|firm|confiden|tight|grip",
    "ล่ม": r"sink|sunk|capsiz|collaps|fall",
    "กั้น": r"separat|block|wall|ward|barrier|impermeab|veil|apotrop|keep",
    "ทั่ง": r"anvil",
    "แท่น": r"pedestal|altar|plinth|dais",
    "ย่าม": r"sack|bag|pouch",
    "เดี่ยว": r"single|toe-to-toe|solo|alone",
    "พลัด": r"fell|fall",
    "ฝั่ง": r"shore|coast|bank",
    "ขั้ว": r"pole|polar",
    "รั้ง": r"held|hold|grab|restrain|took",
    "หนี้": r"debts?",
    "ย้อม": r"dye|colou?r|highlight",
    "ใส": r"clear|transparent",
    "คอย": r"wait",
    "ส้ม": r"citrus|orange",
    "ซุ้ม": r"alcove|arbou?r|bower",
    "สวน": r"garden|orchard|grove",
    "แห้ง": r"dried|dry",
    "ร้าง": r"ruin|abandon|deserted",
    "ทาน": r"alms",
    "หลาบ": r"welt|teach|lesson",
    # ral_swaps: ความหมายของคำที่เสนอ (ข้อ 2) — ไม่มีในอังกฤษ = ไม่มีหลักฐานให้เปลี่ยน
    "ลุกขึ้น": r"stand|get up|got up|rise|rose|risen",
    "แรก": r"first|start|beginning|outset",
    "ลัก": r"steal|stole|theft|thie",
    "รับ": r"receiv|accept|got|get|take|took",
    "ลอง": r"try|tried|attempt|taste",
    "กลับมา": r"return|back|came back",
    "กูล": r"ghoul",
    "ลองของ": r"test|try|challenge",
    "รายตัว": r"each|individual|one by one",
    "ทางรอด": r"survive|escape|way out",
    "ลอดผ่าน": r"crawl|squeeze|pass under|through",
    "ร่ำไป": r"always|constantly|forever",
    "ระคน": r"mix|mingl|blend",
    "ระแบบ": r"system",
    "สามล้อ": r"tricycle|rickshaw",
    "ไล่เลียง": r"question|interrogat|grill",
    "ลือเลื่อง": r"famous|renown|legendary",
    # คำที่เสนอบ่อยใน wrong_word — ความหมายไม่มีในอังกฤษ = เครื่องมือเดาจากบริบทไทยล้วน
    "ใช้": r"use|using|wield|spend|spent|apply|employ",
    "รู้": r"know|knew|aware|understand|realiz|learn|tell|told|wonder",
    "ร่วม": r"join|together|share|participat|along",
    "ม้า": r"horse|mare|steed|mount|stallion|roach",
    "ยอม": r"agree|allow|let|surrender|yield|give in|accept|consent|permit",
    "พ่อ": r"father|dad|pa|da|sire|papa",
    "พอ": r"enough|as good as|about as|suffic",
    "แม่": r"mother|mum|mom|ma|mama",
    "แม้": r"even|though|although|while",
    "สี่": r"four|quarter",
    "สี": r"colou?r|paint|white|red|blue|green|black|hue",
    "ไหล่": r"shoulder",
    "เหล้า": r"wine|ale|drink|booze|vodka|liquor|mead|spirits|beer",
    "ค่ำ": r"evening|night|dusk",
    "ยิง": r"shoot|shot|fire|arrow",
    "ล้อ": r"wheel|roll|cart|wagon",
    "ใคร่": r"curious|wish|desire|lust|eager",
    "สั่ง": r"order|command|instruct",
    "ห้า": r"five|fifth",
    "หา": r"seek|find|look|search|fetch",
    "บาง": r"thin|some",
    "บ้าง": r"some|any|what",
    "นำ": r"lead|led|bring|brought|guide",
    "น้ำ": r"water|element|liquid|drink|stream|river",
    "ทีนี้": r"now|then|so",
    "ที่นี่": r"here",
    "หมู่": r"group|among|village|all of",
    "ว่าง": r"free|available|busy|empty|spare|vacant",
    "วาง": r"put|place|set|lay|down",
    "เขา": r"he|him|his|they|them|she|her|horns?",
    "ไว": r"quick|fast|swift|soon|rapid",
    "บาน": r"mirrors?|doors?|windows?|blossom|bloom|panes?",
    "ขี่": r"ride|rode|riding|mount",
    "แทง": r"stab|stuck|pierc|thrust|impal",
    "ปรับ": r"tinker|adjust|tune|fix|modif",
    "พลาง": r"while|shrug",
    "เร้า": r"arous|excit|stimul|passion",
    "สงสาร": r"pity|sorry|compassion",
}

def _compile(pattern: str) -> re.Pattern:
    """ขึ้นต้นคำเสมอ (trembl → trembling) แต่คำสั้น ≤ 3 ตัวต้องจบคำด้วย (pa ไม่ใช่ past, so ไม่ใช่ some)"""
    alts = [a + r"\b" if re.fullmatch(r"[a-z]{1,3}", a) else a for a in pattern.split("|")]
    return re.compile(rf"\b(?:{'|'.join(alts)})", re.IGNORECASE)


_COMPILED = {w: _compile(p) for w, p in SENSES.items()}


_MARK = re.compile("[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e]")


def _keys(side: str, against: str) -> list:
    """คำใน SENSES ที่ตรงกับฝั่งนี้ — ral_swaps เสนอเป็นช่วงคำ (แต่แลก → แต่แรก) จึงยอมให้คำยาว
    ตั้งแต่ 3 อักษรอยู่ข้างในได้ (แรก ใน แต่แรก) ถ้าไม่มีสระ/วรรณยุกต์ต่อท้าย (หมู ใน หมู่ ไม่ใช่คำนั้น)
    ส่วนคำ 2 อักษรต้องตรงทั้งคำ (ลา ใน ลาเพ ไม่ใช่ ลา)"""
    if side in _COMPILED:
        return [_COMPILED[side]]
    out = []
    for w, r in _COMPILED.items():
        k = side.find(w)
        if len(w) >= 3 and k >= 0 and w not in against and not _MARK.match(side[k + len(w):k + len(w) + 1]):
            out.append(r)
    return out


def load_english() -> dict[int, str]:
    """ภาษาอังกฤษจาก en.w3strings ของเกม ($W3_GAME หรือ ~/games/w3) — ไม่มีเกมก็คืน {} (ไม่กรอง)"""
    import os
    try:
        from core.game_detect import identify
        from core.text_builder import _load_merged
        game = identify(os.environ.get("W3_GAME") or os.path.expanduser("~/games/w3"))
        merged = _load_merged(game, "en", [])
        return merged.strings if merged else {}
    except Exception as exc:
        print("  (ไม่มีภาษาอังกฤษจากเกม — ไม่กรองด้วยต้นฉบับ:", exc, ")")
        return {}


def english_of(en: dict[int, str], src: str, key: str) -> str:
    return en.get(int(key), "") if src == "strings" and key.isdigit() else ""


def ruled_out(word: str, alt: str, english: str) -> bool:
    """True เมื่ออังกฤษยืนยันว่าคำเดิมถูก หรือไม่มีความหมายของคำที่เสนอเลย"""
    if not english:
        return False
    mine, other = _keys(word, alt), _keys(alt, word)
    if any(r.search(english) for r in mine):
        return True
    return bool(other) and not any(r.search(english) for r in other)
