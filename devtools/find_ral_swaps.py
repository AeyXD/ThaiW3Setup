"""สร้าง devtools/ral_swaps.csv — คำสะกดผิดแบบสลับ ร↔ล ในคำแปล (assets/translations.json.gz)

รันซ้ำได้ทุกครั้งที่คลังแปลอัปเดต:
    .venv/bin/python devtools/find_ral_swaps.py            # เขียน devtools/ral_swaps.csv + สรุป
    .venv/bin/python devtools/find_ral_swaps.py -o /tmp/x.csv

คลาสนี้ตัวตรวจคำสะกดทั่วไปจับไม่ได้ เพราะทุกพยางค์เป็นคำจริง (บุกลุก = บุก+ลุก)
จึงตรวจสองระดับบนผลตัดคำของ core/thai_wrap โดยแยกเป็น**ช่วงอักษรไทยต่อช่วง**ก่อนตัดคำ
(ตัดทั้งข้อความก้อนเดียวจะทำให้เครื่องหมาย/แท็กที่ติดคำ อย่าง บุกลุก! หรือ <b>บุกลุก</b>
เกาะเป็น token เดียวแล้วหลุดเงื่อนไขภาษาไทย):
- token เดี่ยว: คำที่ไม่อยู่ในคลังศัพท์ แต่สลับ ร↔ล หนึ่งตำแหน่งแล้วกลายเป็นคำจริง
- คำประสม: token ติดกัน 2-3 ตัวที่รวมกันไม่ใช่คำ แต่สลับหนึ่งตำแหน่งแล้วเป็นคำ (บุก+ลุก → บุกรุก)

การกรอง (สำคัญกับ reviewer):
- **ทุกแถวเป็นข้อเสนอของเครื่องมือ ไม่มีแถวไหน "ยืนยันแล้ว" ในตัว** — การยืนยันเกิดทีละ
  ข้อความโดยทีมแปลใน Google Sheets เท่านั้น (token ที่ดูผิดในบริบทหนึ่ง อาจถูกในอีกบริบท
  เช่น ตลอดการเดินทาง ถูก แต่ ตลอดการเลย ผิด) จึงไม่มีคอลัมน์ "ข้อความที่แก้แล้ว"
  ให้ทีมแก้เองจากบริบทที่แนบไว้
- ALLOW คือรูปที่ตรวจแล้วว่า**ถูกต้อง** — คำทับศัพท์/ชื่อเฉพาะ (วิลโลว์ เฟรย่า บาลิสต้า)
  คำประสมที่ถูกแต่โดนจับคร่อมขอบ token (การรุก ทำรายได้ ถั่วและ) และคำจริงที่คลังศัพท์
  ยังไม่มี (จราจล ลางๆ) ชื่อที่เพิ่มเข้า ALLOW ต้องมาจากการตรวจทานของทีมเสมอ
- HINTS/CONTEXT_HINTS คือคำที่ผิดจริงแต่คำแก้ไม่ได้มาจากการสลับ (รุงแรง→รุนแรง) —
  ใช้เป็นข้อเสนอที่ดีกว่ากลไกสลับ โดยรูปที่แก้ผิดง่าย (ไหร) จะเสนอเฉพาะเมื่อมี
  บริบทกำกับ: หลัง เท่า = ไหร่ แต่หลัง สมุน = สมุนไพร
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.thai_wrap import BREAK, ThaiWrapper, load_words

DEFAULT_STORE = Path(__file__).resolve().parent.parent / "assets" / "translations.json.gz"
DEFAULT_OUT = Path(__file__).resolve().parent / "ral_swaps.csv"

# รูปที่ตรวจทานแล้วว่าถูกต้อง — อย่ารายงาน
ALLOW = {
    # คำจริงที่คลังศัพท์ยังไม่มี / การสะกดที่ยอมรับ (key เป็นทั้งรูปเต็มและ token ที่ตัวตัดคำแยกออก)
    "จราจล", "จรา", "ลางๆ", "รำรึก", "รึก",
    # คำทับศัพท์และชื่อเฉพาะ
    "วิลโลว์", "วิล", "โอริโอล", "โอล", "เฟรย่า", "เฟร", "ลินเดน", "ไฮโรด",
    "ริดดิก", "สเกลลิก", "บรูซา", "บาลิสต้า", "คาโนลา", "กางเกงเร", "มารี", "โนลา",
    "โครต", "โคร", "มาริน",
    # คำประสมที่ถูกต้องแต่กลไกจับคร่อมขอบ token
    "การแปล", "การแปลง", "ทำรายได้", "ทำราย", "การรุก", "ถั่วและ", "โดยลอบ", "ลับได้",
    "ที่รับ", "นางกลาย", "จะกระ", "รับตัว", "ไร่ที่", "ไรเลย", "ว่ากาล",
    "การลด", "ดำลง", "เป็นลัง", "ติดแล้ว", "ที่ล้าง", "ถือพร", "การลัด",
    "ละดู", "กันไกล", "ลับสัมผัส", "ดูกล", "ดีระ", "ร่วงเลย", "ให้พล",
    "การออก", "ลังแรก", "รูนะ", "การอ", "ปรี",
    # คำทับศัพท์ที่ตัวตัดคำแยกเป็นชิ้นสั้น (สเกลลิก ริดดิก ไฮโรด ลินเดน บรูซา)
    "ลิก", "ริด", "โรด", "ลิน", "บรู", "แกร",
    # การลากเสียงในบทพูด (รออออ) และสำนวนพูดที่ใช้ได้ (หลบๆ ซ่อนๆ)
    "รออออ", "รออ", "หลบๆ",
}

# ข้อเสนอระดับคำ: รูปที่ผิดจริงแต่คำแก้ไม่ได้มาจากการสลับ ร↔ล (รุงแรง→รุนแรง)
# ทุกรายการเป็น**ข้อเสนอของเครื่องมือ** ไม่ใช่การยืนยัน — ทีมแปลยืนยันทีละข้อความ
# ใน Google Sheets เท่านั้น จึงจะถือว่ายืนยันแล้ว
HINTS = {
    "รุง": "รุน",            # รุงแรง → รุนแรง
    "ลักษ์": "ลักษณ์",       # สัญลักษ์ → สัญลักษณ์
    "ลังค์": "ลังก์",         # บัลลังค์ → บัลลังก์
    "มาละ": "มาล่ะ",
    "โคลม": "โคลน",          # โคลมตม → โคลนตม
    "อารมเสีย": "อารมณ์เสีย",
    "โรงละคน": "โรงละคร",
    "ตระกลู": "ตระกูล",
    "ร้ำ": "ร่ำ",              # ร้ำลือ → ร่ำลือ
    "แกรง": "แกร่ง",           # แข็งแกรง → แข็งแกร่ง
    "เกรา": "เกราะ",
    "นักเรีย": "นักเรียน",
    "บรอนด์": "บลอนด์",
    "กลู": "กูล",           # ตระกลู → ตระกูล
}

# รูปที่การแก้**ต้องอาศัยบริบท** — token เดียวไม่พอ เพราะคำเดียวกันอยู่ในคำตั้งใจ
# คนละคำ: ไหร หลัง เท่า/เท่าไ = ไหร่ แต่ ไหร หลัง สมุน = สมุนไพร (แก้ทั้งคู่)
CONTEXT_HINTS = {
    ("เท่า", "ไหร"): "เท่าไหร่",
    ("ประมาณ", "ไหร"): "ประมาณไหร่",
    ("สมุน", "ไหร"): "สมุนไพร",
}
# token ที่ไม่มีบริบทกำกับแล้วห้ามเสนอเลย (เสนอผิดง่ายกว่าเสนอถูก)
CONTEXT_ONLY = {"ไหร"}

THAI = re.compile(r"^[\u0e00-\u0e7f]+$")


def swap_variants(tok: str) -> list[str]:
    return [tok[:i] + ("ล" if ch == "ร" else "ร") + tok[i + 1:]
            for i, ch in enumerate(tok) if ch in "รล"]


def load_entries(store: Path):
    """yield (แหล่ง, id, ข้อความ) จากคลังแปล — รูปแบบเดียวกับ find_typos.py"""
    data = json.load(gzip.open(store, "rt", encoding="utf-8"))
    for key, value in data.get("strings", {}).items():
        yield "strings", key, value
    for key, value in data.get("text", {}).items():
        yield "text", key, value


def scan_text(text: str, wrapper: ThaiWrapper, lexicon: set[str]):
    """คืน [(รูปผิด, ข้อเสนอ, start, end)] ตำแหน่งอ้างอิงต้นฉบับ

    ตรวจเป็นช่วงอักษรไทยต่อช่วง: ถ้าตัดคำทั้งข้อความก้อนเดียว เครื่องหมายหรือแท็ก
    ที่ติดกับคำ (บุกลุก! / <b>บุกลุก</b>) จะเกาะเป็น token เดียวแล้วหลุดเงื่อนไขภาษาไทย
    """
    hits = []
    for run in re.finditer(r"[\u0e00-\u0e7f]+", text):
        base = run.start()
        toks = wrapper.wrap(run.group()).split(BREAK)
        starts, pos = [], base
        for t in toks:
            starts.append(pos)
            pos += len(t)
        # พาส 0: ข้อเสนอที่ต้องมีบริบทกำกับ (แก้คู่คำเป็นคำเดียว เช่น สมุนไหร → สมุนไพร)
        for i, tok in enumerate(toks):
            if i == 0:
                continue
            fix = CONTEXT_HINTS.get((toks[i - 1], tok))
            if fix:
                start = starts[i - 1]
                wrong = text[start:starts[i] + len(tok)]
                hits.append((wrong, fix, start, starts[i] + len(tok)))
        # พาส 1: token เดี่ยว
        for tok, start in zip(toks, starts):
            if not (THAI.match(tok) and len(tok) >= 3 and tok not in lexicon and tok not in ALLOW):
                continue
            if tok in CONTEXT_ONLY:
                continue  # มีเฉพาะพาส 0 เท่านั้น
            for v in swap_variants(tok):
                if v in lexicon:
                    hits.append((tok, HINTS.get(tok, v), start, start + len(tok)))
                    break
        # พาส 2: คำประสม 2-3 token ติดกัน
        for span in (2, 3):
            for i in range(len(toks) - span + 1):
                chunk = toks[i:i + span]
                if not all(len(t) >= 2 for t in chunk):
                    continue
                joined = "".join(chunk)
                if joined in lexicon or joined in ALLOW:
                    continue
                for v in swap_variants(joined):
                    if v in lexicon:
                        start = starts[i]
                        hits.append((joined, HINTS.get(joined, v), start, start + len(joined)))
                        break
    # ตัด hit ที่ซ้อนอยู่ใน hit ที่ยาวกว่า (เด็กกำพล้า ครอบ กำพล้า อยู่รายงานเดียว)
    hits.sort(key=lambda h: (h[2], -(h[3] - h[2])))
    kept = []
    for hit in hits:
        if not any(k[2] <= hit[2] and hit[3] <= k[3] and k[0] != hit[0] for k in kept):
            kept.append(hit)
    return kept


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-s", "--store", type=Path, default=DEFAULT_STORE, help="ไฟล์ translations.json.gz")
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help="ไฟล์ CSV ปลายทาง")
    args = ap.parse_args()

    lexicon = load_words()
    wrapper = ThaiWrapper(lexicon)
    entries = list(load_entries(args.store))
    rows = []
    per_form = Counter()
    for source, key, text in entries:
        if not isinstance(text, str):
            continue
        for wrong, right, s, e in sorted(set(scan_text(text, wrapper, lexicon))):
            per_form[wrong] += 1
            ctx = text[max(0, s - 25):e + 25].replace("\n", " ")
            rows.append(("ข้อเสนอเครื่องมือ", source, key, wrong, right, ctx))

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ประเภท", "แหล่ง", "id", "คำที่สงสัย", "ข้อเสนอ", "บริบท"])
        writer.writerows(rows)

    print(f"เขียน {args.out} — {len(rows)} แถว จากคลัง {len(entries)} รายการ")
    print(f"รูปที่สงสัย {len(per_form)} รูป รวม {sum(per_form.values())} ครั้ง — 20 อันดับแรก:")
    for wrong, n in per_form.most_common(20):
        print(f"  {wrong}: {n}")


if __name__ == "__main__":
    main()
