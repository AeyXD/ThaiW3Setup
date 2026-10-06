"""สร้าง devtools/wrong_word.csv — คำที่**สะกดถูก**แต่**ผิดความหมาย**ในบริบท (คลัง translations.json.gz)

รันซ้ำได้ทุกครั้งที่คลังแปลอัปเดต:
    .venv/bin/python devtools/find_wrong_word.py            # เขียน devtools/wrong_word.csv + สรุป
    .venv/bin/python devtools/find_wrong_word.py -o /tmp/x.csv

คลาสนี้ยากที่สุดของบรรดา typo: รูปที่ผิดเป็นคำจริงเต็มตัว ตัวตรวจคำสะกดและตัวตัดคำ
ยอมให้ผ่านเสมอ จึงต้องใช้**บริบท**ตัดสิน หลักการคือ confusion set + collocation:

1. ชุดคำสับสน: คู่คำจริงในคลังศัพท์ (thai_words) ที่ต่างกันไม่เกินรูปแบบเสียงหนึ่งอย่าง
   - วรรณยุกต์ต่างกัน (เขา/เข่า/เข้า, ชา/ช้า, ปา/ป่า/ป้า)
   - สระในกลุ่ม ั/ะ/า ต่างกัน (จัง/จาง)
   - ตัวท้าย ร/ล ต่างกัน (การ/กาล)
2. คะแนนบริบท: นับ bigram (คำหน้า,คำหลัง) ของทั้งคลัง แล้วดูว่าการปรากฏแต่ละจุด
   คำตัวไหนเคยอยู่คู่เพื่อนบ้านแบบนี้ทั่วคลัง (เข้าไปใน = ทั่วไป / เข่าไปใน = ไม่เคยมี)
   โดยตัดคำแบบ**แยกช่วงอักษรไทยต่อช่วง** ไม่ให้เครื่องหมายหรือแท็กที่ติดคำ
   (เข้า! / <b>เข้า</b>) เกาะเป็น token เดียวจนหลุดเงื่อนไข
3. รายงานเมื่อคำในข้อความ**แทบไม่เคย**ปรากฏในบริบทนั้น (≤ MAX_MINE ครั้ง — typo
   ชอบซ้ำกันเองในคลัง) ขณะที่คู่สับสนตัวอื่นในชุดปรากฏในบริบทแบบเดียวกัน**แน่นอน**
   (≥ MIN_SUPPORT ครั้ง) ซึ่งมักคือคำที่ตั้งใจจะพิมพ์

การกรอง (สำคัญกับ reviewer):
- **ทุกแถวเป็นข้อเสนอของเครื่องมือ** — ไม่มีคอลัมน์ "ข้อความที่แก้แล้ว" เพราะการยืนยัน
  เกิดทีละข้อความโดยทีมแปลใน Google Sheets เท่านั้น ไม่ใช่ที่ระดับคำ
- ค่า MIN_SUPPORT สูงและ MAX_MINE ต่ำ เพื่อแลกกับจำนวนผลที่น้อย
  เพราะคลาสนี้หายากและ false positive แพง (คำถูกมาสะกดผิดไปเอง)
- คำฟุ่มเฟือยที่วัดแล้ว noise มาก (คำสั้นมาก/คำที่ครอบคลุมหลายความหมาย) อยู่ใน ALLOW
- ผลทั้งหมดเป็น**ข้อเสนอ**ระดับ id ให้ทีมแปลยืนยันใน Google Sheets ก่อนเข้าคลังเสมอ
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.thai_wrap import BREAK, ThaiWrapper, load_words

DEFAULT_STORE = Path(__file__).resolve().parent.parent / "assets" / "translations.json.gz"
DEFAULT_OUT = Path(__file__).resolve().parent / "wrong_word.csv"

TONES = "\u0e48\u0e49\u0e4a\u0e4b"  # ่ ้ ๊ ๋
THAI = re.compile(r"^[\u0e00-\u0e7f]+$")
# คำเดิมต้องแทบไม่เคยอยู่บริบทนี้ (ยอมได้ 1 ครั้ง — typo ชอบซ้ำกันเองในคลังเดียว)
MAX_MINE = 1
# คู่สับสนต้องเคยอยู่บริบทนี้อย่างน้อยเท่าไหร่จึงนับว่า "แน่นอน"
MIN_SUPPORT = 5
MIN_LEN = {"tone": 2, "vowel": 4, "final": 4}

# คู่ที่ตรวจทานกับบริบทแล้วว่ารูปเดิม**ถูกต้อง** — เพิ่มได้เรื่อย ๆ หลังทีมตรวจ
# ส่วนใหญ่เป็นคำลงท้ายประโยคที่เลือกเครื่องหมายได้ตามสไตล์ภาษาพูด (นั่น/นั้น น่ะ/นะ)
ALLOW_PAIRS = {
    ("นั่น", "นั้น"), ("นั้น", "นั่น"), ("น่ะ", "นะ"), ("นะ", "น่ะ"),
    ("ล่ะ", "ละ"), ("ละ", "ล่ะ"), ("นี่", "นี้"), ("นี้", "นี่"),
    ("จ๊ะ", "จะ"), ("จ้ะ", "จะ"), ("มั้ย", "ม่าย"), ("มั้ง", "มั่ง"), ("มั่ง", "มั้ง"),
    ("เอ่อ", "เออ"), ("เอ้ย", "เอ๊ย"), ("เอ่ย", "เอ๊ย"), ("แหง๋", "แหง"),
    ("วะ", "ว่ะ"), ("ว่ะ", "วะ"), ("อา", "อ่า"), ("ไม๊", "ไม่"),
    ("นั่นแหละ", "นั้นแหละ"), ("นี่แหละ", "นี้แหละ"), ("นี้แหละ", "นี่แหละ"),
    # ตรวจกับต้นฉบับ/บริบทแล้วรูปเดิมถูก: รังเจ้าตะขาบ = centipede nests,
    # ม้าดีกว่าวิทเชอร์ = ม้าจริง, ทีนี้ไปไหนต่อ = "now then", ไปที่บ่อ = บ่อน้ำจริง,
    # หิน 5 ก้อน = ลักษณนาม, เค้านต์/เค้าท์ = ยศ Count
    ("รัง", "รั้ง"), ("ม้า", "มา"), ("ทีนี้", "ที่นี่"), ("บ่อ", "บอ"),
    ("วันที", "วันที่"), ("ก้อน", "ก่อน"), ("เค้า", "เคา"),
    # ปวดข้อ, ค่อยย้ำเตือน, ย้อมด้วยกานพลู, ไม้โกย (pitchfork), ราชาเหนือเผ่า, คนไร่,
    # โรคร้าย, ไหม้ธุลี (บทกวี), วิธีหนี, ชอบเสี่ยง, ส่วนท้าย — รูปเดิมถูกในบริบทเหล่านี้
    ("ข้อ", "ขอ"), ("ค่อย", "คอย"), ("ย้อม", "ยอม"), ("ไม้", "ไม่"),
    ("เผ่า", "เผา"), ("ไร่", "ไร้"), ("ร้าย", "ราย"), ("ไหม้", "ไหม"),
    ("หนี", "หนี้"), ("เสี่ยง", "เสียง"), ("ส่วน", "สวน"),
    # ยืนยันโดยทีมแปล: "มีข่ายเวทมนตร์มาปกป้องถ้ำ" ถูกต้องตามต้นฉบับแล้ว (ไม่ใช่ ขาย)
    ("ข่าย", "ขาย"),
}


def skeletons(word: str):
    """คีย์จัดกลุ่มสำหรับสร้างคู่สับสนสามแบบ"""
    toneless = re.sub(f"[{TONES}]", "", word)
    yield "tone", toneless
    if len(word) >= MIN_LEN["vowel"]:
        yield "vowel", toneless.replace("ะ", "า").replace("ั", "า")
        yield "final", re.sub("ร$", "ล", toneless)


def confusion_sets(lexicon: set[str]) -> dict[str, set[str]]:
    """word → คำอื่นในคลังที่อยู่ชุดสับสนเดียวกัน"""
    groups = defaultdict(set)
    for w in lexicon:
        if not THAI.match(w) or len(w) > 10:
            continue
        for kind, key in skeletons(w):
            if len(w) >= MIN_LEN[kind]:
                groups[(kind, key)].add(w)
    out = defaultdict(set)
    for (_kind, _key), members in groups.items():
        if len(members) < 2:
            continue
        for w in members:
            out[w] |= members - {w}
    return out


def load_entries(store: Path):
    data = json.load(gzip.open(store, "rt", encoding="utf-8"))
    for key, value in data.get("strings", {}).items():
        yield "strings", key, value
    for key, value in data.get("text", {}).items():
        yield "text", key, value


def runs_of(text: str, wrapper: ThaiWrapper):
    """[(จุดเริ่มในข้อความ, token)] ต่อช่วงอักษรไทย — แยกช่วงก่อนตัดคำ ไม่ให้เครื่องหมาย
    หรือแท็กที่ติดคำ (เข้า! / <b>เข้า</b>) เกาะเป็น token เดียวจนหลุดเงื่อนไขภาษาไทย"""
    out = []
    for m in re.finditer(r"[\u0e00-\u0e7f]+", text):
        toks = wrapper.wrap(m.group()).split(BREAK)
        if len(toks) > 1:
            out.append((m.start(), toks))
    return out


def scan_text(text: str, runs, confusions: dict, bigrams: Counter):
    """คืน [(คำที่สงสัย, ข้อเสนอ, จุดเริ่ม)] — เทียบบริบท**ทีละด้าน**ด้วยเกณฑ์เดียวกัน

    ด้านหนึ่งถือเป็นหลักฐานเมื่อคำเดิมแทบไม่เคยอยู่คู่เพื่อนบ้านด้านนั้น (≤ MAX_MINE —
    typo ชอบซ้ำกันเองในคลัง) ขณะที่คู่สับสนอยู่คู่แบบเดียวกันแน่นอน (≥ MIN_SUPPORT)
    เกตใช้ **max** ไม่ใช่ผลรวม เพราะคำกลางประโยคมีเพื่อนบ้านสองด้านเสมอ คำที่ปรากฏครั้ง
    เดียวจึงได้ 1+1=2 แล้วโดนตัดก่อนได้เทียบทางเลือก (เขา|เข่า|ไป — เข่าถูกข้าม) แต่การ
    หายากต้องเป็น**ทั้งสองด้าน** หลักฐานด้านเดียวไม่พอฟันธง (ขา→ข้า ล้นเมื่อไม่มีเกตนี้)
    """
    hits = []
    for base, toks in runs:
        for i, tok in enumerate(toks):
            alts = confusions.get(tok)
            if not alts:
                continue
            prev_t = toks[i - 1] if i > 0 else ""
            next_t = toks[i + 1] if i + 1 < len(toks) else ""
            mine = (bigrams[(prev_t, tok)], bigrams[(tok, next_t)])
            if max(mine) > MAX_MINE:
                continue  # คำเดิมเคยอยู่คู่เพื่อนบ้านด้านใดด้านหนึ่งแบบปกติ ถือว่าปกติ
            best, support = None, 0
            for alt in alts:
                if (tok, alt) in ALLOW_PAIRS:
                    continue
                for m, a in zip(mine, (bigrams[(prev_t, alt)], bigrams[(alt, next_t)])):
                    if m <= MAX_MINE and a > support:
                        best, support = alt, a
            if not (best and support >= MIN_SUPPORT):
                continue
            start = base + sum(len(t) for t in toks[:i])
            hits.append((tok, best, start))
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-s", "--store", type=Path, default=DEFAULT_STORE, help="ไฟล์ translations.json.gz")
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help="ไฟล์ CSV ปลายทาง")
    args = ap.parse_args()

    lexicon = load_words()
    wrapper = ThaiWrapper(lexicon)
    confusions = confusion_sets(lexicon)

    entries = [(src, key, text) for src, key, text in load_entries(args.store) if isinstance(text, str)]
    entry_runs = []
    bigrams = Counter()
    for _src, _key, text in entries:
        runs = runs_of(text, wrapper)
        entry_runs.append(runs)
        for _base, toks in runs:
            for a, b in zip(toks, toks[1:]):
                bigrams[(a, b)] += 1

    rows = []
    per_form = Counter()
    for (src, key, text), runs in zip(entries, entry_runs):
        for tok, best, start in scan_text(text, runs, confusions, bigrams):
            ctx = text[max(0, start - 25):start + len(tok) + 25].replace("\n", " ")
            per_form[f"{tok} → {best}"] += 1
            rows.append(("ข้อเสนอเครื่องมือ", src, key, tok, best, ctx))

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ประเภท", "แหล่ง", "id", "คำที่สงสัย", "ข้อเสนอ", "บริบท"])
        writer.writerows(rows)

    print(f"ชุดสับสน: {sum(len(v) for v in confusions.values()) // 2:,} คู่ จากคลังศัพท์ {len(lexicon):,} คำ")
    print(f"เขียน {args.out} — {len(rows)} แถว จากคลัง {len(entries)} รายการ")
    for form, n in per_form.most_common(30):
        print(f"  {form}  x{n}")


if __name__ == "__main__":
    main()
