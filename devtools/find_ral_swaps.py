"""สร้าง devtools/ral_swaps.csv — คำสะกดผิดแบบสลับ ร↔ล ในคำแปล (assets/translations.json.gz)

รันซ้ำได้ทุกครั้งที่คลังแปลอัปเดต:
    .venv/bin/python devtools/find_ral_swaps.py            # เขียน devtools/ral_swaps.csv + สรุป
    .venv/bin/python devtools/find_ral_swaps.py -o /tmp/x.csv

คลาสนี้ตัวตรวจคำสะกดทั่วไปจับไม่ได้ เพราะทุกพยางค์เป็นคำจริง (บุกลุก = บุก+ลุก)
จึงตรวจสองระดับบนผลตัดคำของ core/thai_wrap:
- token เดี่ยว: คำที่ไม่อยู่ในคลังศัพท์ แต่สลับ ร↔ล หนึ่งตำแหน่งแล้วกลายเป็นคำจริง
- คำประสม: token ติดกัน 2-3 ตัวที่รวมกันไม่ใช่คำ แต่สลับหนึ่งตำแหน่งแล้วเป็นคำ (บุก+ลุก → บุกรุก)

การกรอง (สำคัญกับ reviewer):
- ALLOW คือรูปที่ตรวจทานแล้วว่า**ถูกต้อง** — คำทับศัพท์/ชื่อเฉพาะ (วิลโลว์ เฟรย่า บาลิสต้า)
  คำประสมที่ถูกแต่โดนจับคร่อมขอบ token (การรุก ทำรายได้ ถั่วและ) และคำจริงที่คลังศัพท์ยังไม่มี (จราจล ลางๆ)
  ชื่อที่เพิ่มเข้า ALLOW ต้องมาจากการตรวจทานของทีมเสมอ
- OVERRIDES คือรูปที่ผิดจริงแต่คำที่ถูก**ไม่ได้มาจากการสลับ ร↔ล** (รุงแรง→รุนแรง ไหร→ไหร่)
  รายงานด้วยคำแก้ที่ตรวจทานแล้วแทนคำแก้จากกลไกสลับ
ผลลัพธ์ทั้งหมดเป็น**ข้อเสนอ**ระดับ id ให้ทีมแปลยืนยันใน Google Sheets ก่อนเข้าคลังเสมอ
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
    "โครต", "โคร",
    # คำประสมที่ถูกต้องแต่กลไกจับคร่อมขอบ token
    "การแปล", "การแปลง", "ทำรายได้", "ทำราย", "การรุก", "ถั่วและ", "โดยลอบ", "ลับได้",
    "ที่รับ", "นางกลาย", "จะกระ", "รับตัว", "ไร่ที่", "ไรเลย", "ว่ากาล",
    "การลด", "ดำลง", "เป็นลัง", "ติดแล้ว", "ที่ล้าง", "ถือพร", "การลัด",
    "ละดู", "กันไกล", "ลับสัมผัส", "ดูกล", "ดีระ", "ร่วงเลย", "ให้พล",
    "การออก", "ลังแรก", "รูนะ", "การอ", "ปรี",
    # คำทับศัพท์ที่ตัวตัดคำแยกเป็นชิ้นสั้น (สเกลลิก ริดดิก ไฮโรด ลินเดน บรูซา)
    "ลิก", "ริด", "โรด", "ลิน", "บรู", "แกร",
    # การลากเสียงในบทพูด (รออออ)
    "รออออ", "รออ",
}

# รูปที่ผิดจริง แต่คำที่ถูกไม่ได้มาจากการสลับ ร↔ล — ตรวจทานแล้ว ใช้คำแก้นี้แทน
# key ต้องเป็นรูปที่สแกนเนอร์รายงานจริง (= token เดี่ยวหรือคำประสมที่แยกได้)
OVERRIDES = {
    "รุง": "รุน",            # รุงแรง → รุนแรง
    "ไหร": "ไหร่",
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
    """คืน [(รูปผิด, คำแก้, start, end)] ของข้อความหนึ่ง条 พร้อมตัดผลที่ซ้อนในผลที่ยาวกว่า"""
    toks = wrapper.wrap(text).split(BREAK)
    starts, pos = [], 0
    for t in toks:
        starts.append(pos)
        pos += len(t)
    hits = []
    # พาส 1: token เดี่ยว
    for tok, start in zip(toks, starts):
        if THAI.match(tok) and len(tok) >= 3 and tok not in lexicon and tok not in ALLOW:
            for v in swap_variants(tok):
                if v in lexicon:
                    hits.append((tok, OVERRIDES.get(tok, v), start, start + len(tok)))
                    break
    # พาส 2: คำประสม 2-3 token ติดกัน
    for span in (2, 3):
        for i in range(len(toks) - span + 1):
            chunk = toks[i:i + span]
            if not all(THAI.match(t) and len(t) >= 2 for t in chunk):
                continue
            joined = "".join(chunk)
            if joined in lexicon or joined in ALLOW:
                continue
            for v in swap_variants(joined):
                if v in lexicon:
                    start = starts[i]
                    hits.append((joined, OVERRIDES.get(joined, v), start, start + len(joined)))
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
        hits = scan_text(text, wrapper, lexicon)
        if not hits:
            continue
        unique = sorted(set(hits))
        for wrong, right, _s, _e in unique:
            per_form[wrong] += 1
        fixed = text
        # แทนที่ตามตำแหน่งที่จับไว้เท่านั้น (ทำจากท้ายมาหน้า) — text.replace ทั้งข้อความ
        # จะถูกข้างในคำอื่น เช่น รุง→รุน ทำลายคำว่า ปรุง ในประโยคเดียวกัน
        for wrong, right, s, e in sorted(unique, key=lambda h: -h[2]):
            if fixed[s:e] == wrong:
                fixed = fixed[:s] + right + fixed[e:]
        for wrong, right, _s, _e in unique:
            cat = "สลับ ร↔ล (คำแก้ตรวจทาน)" if OVERRIDES.get(wrong) == right else "สลับ ร↔ล"
            rows.append((cat, source, key, f"{wrong} → {right}", text, fixed))

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ประเภท", "แหล่ง", "id", "คำที่แก้", "ปัจจุบัน", "ที่ควรเป็น"])
        writer.writerows(rows)

    print(f"เขียน {args.out} — {len(rows)} แถว จากคลัง {len(entries)} รายการ")
    print(f"รูปผิด {len(per_form)} รูป รวม {sum(per_form.values())} ครั้ง — 20 อันดับแรก:")
    for wrong, n in per_form.most_common(20):
        print(f"  {wrong}: {n}")


if __name__ == "__main__":
    main()
