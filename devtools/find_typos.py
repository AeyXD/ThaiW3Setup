"""สร้าง typos.csv — รายการคำสะกดผิดในคำแปลที่พบในคลัง (assets/translations.json.gz)

รันซ้ำได้ทุกครั้งที่คลังแปลอัปเดต เพื่อเช็คความคืบหน้าของทีมแปล:
    .venv/bin/python devtools/find_typos.py            # เขียน typos.csv ในโฟลเดอร์ชั่วคราวของระบบ + สรุป
    .venv/bin/python devtools/find_typos.py -o /tmp/x.csv

ผลเป็น snapshot ของคลังตอนที่รัน จึงไม่ commit ไว้ใน repo — คำแก้จริงอยู่ที่ชีตของทีมแปล

หลักการกรอง (สำคัญกับ reviewer):
- ตัวอักษรฐานซ้ำ เช่น าา (อาา = ลากเสียงในบทพูด) หรือ กกก (ฮั่กกก) **ไม่ถูกจับ**
  จับเฉพาะสระจ่อย/วรรณยุกต์/ไม้ที่ซ้ำกันเอง เพราะพยัญชนะหนึ่งตัวใส่เครื่องหมายชนิดเดียวกัน
  ซ้ำไม่ได้ในภาษาไทย
- เ+เ สองตัวติดกันแทน แ จับทั้งชุดอย่างปลอดภัย เพราะคำไทยไม่ลงท้ายด้วยสระเอ
  (สระหน้าต้องมีพยัญชนะตามเสมอ)
- คำเฉพาะ (จักรพรรดิ มงกุฎ คนแคระ บันได เวท เวทมนตร์ ปฏิ ใฝ่ ใช่ ถิ่นฐาน เริงร่า เต้นรำ ที่) เป็นรายการตายตัวจากการตรวจทานของทีม
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_STORE = Path(__file__).resolve().parent.parent / "assets" / "translations.json.gz"
DEFAULT_OUT = Path(tempfile.gettempdir()) / "typos.csv"

# สระจ่อย/วรรณยุกต์/ไม้ที่ซ้ำกันเองไม่ได้: ั ิ ี ึ ื ุ ู ็ ่ ้ ๊ ๋ ์
# (ตั้งใจไม่รวม ฺ ํ ๎ ตามชุดที่ตรวจทาน — และไม่รวม า เพราะซ้ำแบบลากเสียงถูกต้อง)
DOUBLE_MARKS = "\u0e31\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c"
MARK_RUN = re.compile("([" + DOUBLE_MARKS + "])\\1+")

WORD_FIXES = [
    ("จักพรรดิ ฯลฯ → จักรพรรดิ",
     [("จักรดิพรรดิ", "จักรพรรดิ"), ("จักดิพรรดิ", "จักรพรรดิ"),
      ("จักร์พรรดิ", "จักรพรรดิ"), ("จักพรรดิ", "จักรพรรดิ")]),
    ("มงกุฏ → มงกุฎ", [("มงกุฏ", "มงกุฎ")]),
    ("คนเคราะ/คนเคระ → คนแคระ", [("คนเคราะ", "คนแคระ"), ("คนเคระ", "คนแคระ")]),
    ("บรรได → บันได", [("บรรได", "บันได")]),
    # ไม่มีคำไหนมี "เวทย์" · เวทย์มนต์ ผิดสองที่ จึงแก้ทั้งคำก่อน
    ("เวทย์ → เวท (นักเวท, เวทมนตร์)", [("เวทย์มนต์", "เวทมนตร์"), ("เวทย์", "เวท")]),
    ("เวทมนต์ → เวทมนตร์", [("เวทมนต์", "เวทมนตร์")]),
    # เจอครั้งแรกในซับ Storybook (2026-10-20) แล้วพบว่าในชีตก็มี — ปฎิ ไม่ใช่คำไทย สะกดถูกคือ ปฏิ เสมอ
    ("ปฎิ → ปฏิ", [("ปฎิ", "ปฏิ")]),
    ("ไฝ่ → ใฝ่", [("ไฝ่", "ใฝ่")]),
    ("ถิ่งฐาน → ถิ่นฐาน", [("ถิ่งฐาน", "ถิ่นฐาน")]),
    ("เริ่งร่า → เริงร่า", [("เริ่งร่า", "เริงร่า")]),
    ("เต็นรำ → เต้นรำ", [("เต็นรำ", "เต้นรำ")]),
    ("ปรากฎ → ปรากฏ", [("ปรากฎ", "ปรากฏ")]),
]

# แก้ด้วย regex: ทึ่ง (น่าทึ่ง) กับ ทึ่ม เป็นคำจริง ทึ่ ที่ตามด้วยอย่างอื่นคือ ที่ พิมพ์ผิด
PATTERN_FIXES = [
    ("ทึ่ → ที่ (ยกเว้น ทึ่ง ทึ่ม)", re.compile("ทึ่(?![งม])"), "ที่"),
    # เฉพาะหน้าคำที่ขึ้นต้นด้วย เบื้อง — เบื่องั้น เบื่อง่าย คือ เบื่อ + งั้น/ง่าย ถูกแล้ว
    ("เบื่องหลัง ฯลฯ → เบื้อง", re.compile("เบื่อง(?=หลัง|ต้น|บน|ล่าง|หน้า)"), "เบื้อง"),
    # ประหลา ไม่ใช่คำ — ตัดคำแล้วได้ ประ|หลา ซึ่งมีในพจนานุกรมทั้งคู่ ตัวตรวจอื่นจึงไม่เห็น
    ("ประหลา → ประหลาด", re.compile("ประหลา(?!ด)"), "ประหลาด"),
    # ไม่มีคำไหนเป็น ใช เปล่า ๆ — ผู้เล่นเจอ "ใชมั้ย" ในเกม (2026-10-20) · ที่เจอทั้งหมดคือ ใช่ แต่บางที่อาจเป็น ใช้ ดูบริบทก่อนแก้
    ("ใช → ใช่ (ไม้เอกหาย — หรือ ใช้ ตามบริบท)", re.compile("ใช(?![่้ั])"), "ใช่"),
    # ใ + พยัญชนะ + ั เป็นไปไม่ได้ — ใ เกินมา เช่น เพื่อใชัยชนะ
    ("ใชั → ชั (ใ เกิน)", re.compile("ใช(?=ั)"), "ช"),
]


def fix_double_e(text: str) -> str:
    return text.replace("เเ", "แ") if "เเ" in text else text


def fix_mark_run(text: str) -> str:
    return MARK_RUN.sub(r"\1", text) if MARK_RUN.search(text) else text


def fix_words(text: str, pairs) -> str:
    out = text
    for wrong, right in pairs:
        out = out.replace(wrong, right)
    return out


def load_entries(store: Path):
    """yield (แหล่ง, id, ข้อความ) จากคลังแปล"""
    data = json.load(gzip.open(store, "rt", encoding="utf-8"))
    for key, value in data.get("strings", {}).items():
        yield "strings", key, value
    for key, value in data.get("text", {}).items():
        yield "text", key, value


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-s", "--store", type=Path, default=DEFAULT_STORE, help="ไฟล์ translations.json.gz")
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help="ไฟล์ CSV ปลายทาง")
    args = ap.parse_args()

    rules = [("เ+เ → แ", fix_double_e), ("สระ/วรรณยุกต์ซ้อน", fix_mark_run)]
    rules += [(name, (lambda p: (lambda t: fix_words(t, p)))(pairs)) for name, pairs in WORD_FIXES]
    rules += [(name, (lambda r, n: (lambda t: r.sub(n, t)))(rx, new)) for name, rx, new in PATTERN_FIXES]

    entries = list(load_entries(args.store))
    rows = []
    for category, fix in rules:
        for source, key, text in entries:
            if not isinstance(text, str):
                continue
            fixed = fix(text)
            if fixed != text:
                rows.append((category, source, key, text, fixed))

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ประเภท", "แหล่ง", "id", "ปัจจุบัน", "ที่ควรเป็น"])
        writer.writerows(rows)

    from collections import Counter
    summary = Counter(r[0] for r in rows)
    print(f"เขียน {args.out} — {len(rows)} แถว จากคลัง {len(entries)} รายการ")
    for category, _ in rules:
        print(f"  {category}: {summary[category]}")


if __name__ == "__main__":
    main()
