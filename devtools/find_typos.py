"""สร้าง devtools/typos.csv — รายการคำสะกดผิดในคำแปลที่พบในคลัง (assets/translations.json.gz)

รันซ้ำได้ทุกครั้งที่คลังแปลอัปเดต เพื่อเช็คความคืบหน้าของทีมแปล:
    .venv/bin/python devtools/find_typos.py            # เขียน devtools/typos.csv + สรุป
    .venv/bin/python devtools/find_typos.py -o /tmp/x.csv

หลักการกรอง (สำคัญกับ reviewer):
- ตัวอักษรฐานซ้ำ เช่น าา (อาา = ลากเสียงในบทพูด) หรือ กกก (ฮั่กกก) **ไม่ถูกจับ**
  จับเฉพาะสระจ่อย/วรรณยุกต์/ไม้ที่ซ้ำกันเอง เพราะพยัญชนะหนึ่งตัวใส่เครื่องหมายชนิดเดียวกัน
  ซ้ำไม่ได้ในภาษาไทย
- เ+เ สองตัวติดกันแทน แ จับทั้งชุดอย่างปลอดภัย เพราะคำไทยไม่ลงท้ายด้วยสระเอ
  (สระหน้าต้องมีพยัญชนะตามเสมอ)
- คำเฉพาะ (จักรพรรดิ มงกุฎ คนแคระ บันได) เป็นรายการตายตัวจากการตรวจทานของทีม
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_STORE = Path(__file__).resolve().parent.parent / "assets" / "translations.json.gz"
DEFAULT_OUT = Path(__file__).resolve().parent / "typos.csv"

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
