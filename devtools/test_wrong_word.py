"""คำผิดกลางประโยคต้องถูกเทียบบริบทเหมือนคำปลายประโยค — regression ของเกณฑ์รวมสองด้าน
(เดิมนับ bigram ซ้าย+ขวารวมกัน คำ hapax กลางประโยคได้ 1+1=2 โดน MAX_MINE=1 ตัดก่อนเทียบ)"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.thai_wrap import ThaiWrapper, load_words
from devtools.find_wrong_word import confusion_sets, runs_of, scan_text

lex = load_words()
w = ThaiWrapper(lex)
conf = confusion_sets(lex)

# คลังตั้งฉบับ: (เขา,ไป) แน่น 6 ครั้ง, (เข่า,ไป)/(เขา,เข่า) ไม่เคยมี
training = ["เขาไปไหนทุกครั้ง", "เขาไปบ้านเช้า", "เขาไปกับเรา", "บอกให้เขาไปเอง",
            "เขาไปคนเดียว", "เขาไปที่โรงเตี๊ยม"]
bg = Counter()
for t in training:
    for _b, toks in runs_of(t, w):
        for a, b in zip(toks, toks[1:]):
            bg[(a, b)] += 1
assert bg[("เขา", "ไป")] >= 6, bg[("เขา", "ไป")]

# คำผิดกลางประโยค (เขา|เข่า|ไป) — ต้องนับประโยคเป้าหมายเข้าตัวนับก่อนตรวจ เหมือนการใช้งาน
# จริงที่คลังรวมข้อความที่กำลังตรวจอยู่ด้วย ไม่เช่นนั้น mine เป็น (0,0) และเกณฑ์แบบเดิม
# (sum) ก็ผ่านเคสนี้ เทสต์จะไม่จับบั๊กที่อ้างไว้เลย
target = "เขาเข่าไปไหน"
for _b, toks in runs_of(target, w):
    for a, b in zip(toks, toks[1:]):
        bg[(a, b)] += 1
assert bg[("เขา", "เข่า")] == 1 and bg[("เข่า", "ไป")] == 1, "ประโยคเป้าหมายต้องถูกนับก่อน"
assert bg[("เขา", "เข่า")] + bg[("เข่า", "ไป")] > 1, "เคสนี้ต้องเป็นคำ hapax กลางประโยค (1,1) ที่เกณฑ์ sum ตัดทิ้ง"
mid = scan_text(target, runs_of(target, w), conf, bg)
assert [(t, b) for t, b, _s in mid] == [("เข่า", "เขา")], mid

# คำถูกตามปกติในคลังเดียวกันต้องเงียบ (เขา อยู่คู่ (เขา,ไป) ที่แน่นอยู่แล้ว)
calm = scan_text("เขาไปบ้านเช้า", runs_of("เขาไปบ้านเช้า", w), conf, bg)
assert calm == [], calm

# คำปลายช่วง (มีเพื่อนบ้านด้านเดียว) ยังจับได้ตามเดิม
tail = scan_text("พาเข่าไปหน่อย", runs_of("พาเข่าไปหน่อย", w), conf, bg)
assert any(t == "เข่า" for t, _b, _s in tail), tail

# เครื่องหมาย/แท็กติดคำไม่ทำให้หลุด: ตำแหน่งยังอ้างต้นฉบับถูกต้อง
tagged = "ดูสิ<b>เขาเข่าไป</b>แล้ว"
hits = scan_text(tagged, runs_of(tagged, w), conf, bg)
assert (t := [(t, s) for t, _b, s in hits if t == "เข่า"]), hits
start = t[0][1]
assert tagged[start:start + len("เข่า")] == "เข่า", start

print("test_wrong_word ok")
