# คำอธิบาย mod.io (สองภาษา) สำหรับ 4 หน้า mod

ร่างสำเร็จรูปสำหรับวางในหน้า mod.io — ก่อนอัปโหลดให้แก้สองอย่างเสมอ:

1. **ตัวเลข % คำแปล** — เอาตัวเลขจริงจาก `percent` ใน `build-info.json` ของ build ที่อัปโหลด
2. **ลิงก์ข้ามหน้า** — เติม URL จริงหลังสร้างหน้า mod แต่ละหน้าแล้ว (แทนที่ `<<URL>>`)

หน้า mod.io ใช้ BBCode (`[b]`, `[url=]`) ถ้าช่องกรอกเป็นข้อความเปล่าก็ตัดแท็กออกได้เลย
ชื่อหน้า (Profile name) ให้ตรงชื่อโฟลเดอร์ mod ตามที่ runbook กำหนด

---

## 1. modThaiText (อัปโหลดตัวแรก, unlisted จนกว่าทดสอบ PS5 ผ่าน)

**Tagline / Summary**: แปลข้อความทั้งเกมเป็นภาษาไทย — Thai translation for the entire game

**Tags/หมวดแนะนำ**: Localisation (ถ้าไม่มีให้เลือกหมวดใกล้สุด เช่น GUI หรือ Overhauls)

**คำอธิบาย (ไทย)**:

```
[b]แปลข้อความใน The Witcher 3: Wild Hunt — Remastered เป็นภาษาไทย (แปลแล้วประมาณ 98%)[/b]

ครอบคลุมบทสนทนา คำอธิบายไอเทม Bestiary journal ชื่อเควส และ UI พร้อมการตัดคำไทยในตัว
ให้ข้อความยาวขึ้นบรรทัดใหม่ระหว่างคำโดยไม่ต้องรอช่องว่าง

[b]วิธีใช้[/b]
1. เปิดใช้ mod นี้ในเมนู Mods ของเกม
2. Options > Language > Text Language > ไทย (Thai)
3. [b]ควรเปิดใช้ modThaiFont ด้วยทุกครั้ง[/b] ไม่อย่างนั้นตัวอักษรไทยจะแสดงเป็นสี่เหลี่ยม
   และถ้าอยากได้ซับคัตซีน Storybook ให้เปิด modThaiStoryBook เพิ่ม

[b]ข้อจำกัดบนคอนโซล[/b]
- ซับใช้สี ขนาด และตำแหน่งมาตรฐานของเกม และเป็นซับไทยอย่างเดียว
  (การปรับแต่งซับและโหมดสองภาษามีเฉพาะฉบับ PC)
- เซฟที่สร้างขณะเปิดใช้ mod จะถูกทำเครื่องหมายว่าเป็นเซฟที่ใช้ mod
  และทรอฟี่/achievements จะถูกปิดในเซฟลักษณะนี้
- การย้ายเซฟข้ามแพลตฟอร์มควรเปิดชุด mod เดียวกันทั้งสองฝั่ง
  ไม่อย่างนั้นเซฟอาจโหลดไม่ถูกต้อง

[b]เครดิต[/b]
คำแปลโดยทีมแปล w3tu / Kuntoon และผู้ร่วมแปลทุกคนใน Google Sheets ของชุมชน
ผลงานของแฟนเกม ไม่เกี่ยวข้องกับ CD PROJEKT RED
The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

**Description (English)**:

```
[b]Thai translation for The Witcher 3: Wild Hunt — Remastered (~98% of game text)[/b]

Covers dialogue, item descriptions, the bestiary and journal, quest names and the UI.
Thai line breaking is built in, so long text wraps between words without waiting for
spaces.

[b]How to use[/b]
1. Enable this mod in the in-game Mods menu
2. Options > Language > Text Language > ไทย (Thai)
3. [b]Enable modThaiFont as well[/b] — without it Thai characters show as boxes.
   Add modThaiStoryBook if you want Thai subtitles on the storybook cutscenes.

[b]Console notes[/b]
- Subtitles use the game's default style and are Thai-only
  (subtitle styling and the bilingual mode are PC-only)
- Saves created with mods enabled are flagged, and trophies/achievements are
  disabled on such saves
- When moving saves across platforms, enable the same set of mods on both,
  otherwise saves may load incorrectly

[b]Credits[/b]
Translation by the w3tu / Kuntoon translation team and every contributor in the
community Google Sheets. A fan project, not affiliated with CD PROJEKT RED.
The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

---

## 2. modThaiFont

**Tagline**: ฟอนต์ภาษาไทยสำหรับ UI และซับ — Thai fonts for the UI and subtitles

**Tags/หมวดแนะนำ**: GUI

**คำอธิบาย (ไทย)**:

```
[b]ฟอนต์ภาษาไทยสำหรับ UI และซับ[/b]

ใช้คู่กับ [url=<<modThaiText URL>>]modThaiText[/url] เสมอ — ไม่มี mod นี้แล้วตัวอักษร
ไทยทั้งหมดจะแสดงเป็นสี่เหลี่ยม (tofu) ทั้งในเมนู ซับ และ journal

เปิดใช้ในเมนู Mods ของเกมได้เลย ไม่ต้องตั้งค่าเพิ่ม

ฟอนต์ชุดนี้มาพร้อมเครื่องมือติดตั้งภาษาไทย ThaiW3Setup (ฉบับ PC)
ผลงานของแฟนเกม ไม่เกี่ยวข้องกับ CD PROJEKT RED
The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

**Description (English)**:

```
[b]Thai fonts for the game's UI and subtitles[/b]

Always use together with [url=<<modThaiText URL>>]modThaiText[/url] — without this
mod every Thai character renders as an empty box (tofu) in menus, subtitles and
the journal.

Enable it in the in-game Mods menu; no extra setup needed.

Fonts ship with the ThaiW3Setup installer project (PC edition). A fan project,
not affiliated with CD PROJEKT RED. The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

---

## 3. modThaiStoryBook

**Tagline**: ซับไทยของคัตซีน Storybook — Thai subtitles for the storybook cutscenes

**Tags/หมวดแนะนำ**: Localisation / Movies & Audio (ตามที่ hub มี)

**คำอธิบาย (ไทย)**:

```
[b]ซับภาษาไทยของคัตซีน Storybook[/b]

ใส่ซับไทยให้คัตซีนวาดประกอบ (เช่น ตอนเปิดเรื่องและช่วงเล่าเรื่องระหว่างภาค)
ใช้คู่กับ [url=<<modThaiText URL>>]modThaiText[/url] และ [url=<<modThaiFont URL>>]modThaiFont[/url]

หมายเหตุ: ซับของ Storybook ไม่รับผลจากการปรับสี ขนาด หรือตำแหน่งซับของเกม

เครดิต: ซับโดยทีมแปล w3tu / Kuntoon
ผลงานของแฟนเกม ไม่เกี่ยวข้องกับ CD PROJEKT RED
The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

**Description (English)**:

```
[b]Thai subtitles for the storybook cutscenes[/b]

Adds Thai subtitles to the illustrated storybook sequences (the intro and the
in-between story chapters). Use together with [url=<<modThaiText URL>>]modThaiText[/url]
and [url=<<modThaiFont URL>>]modThaiFont[/url].

Note: storybook subtitles are not affected by the game's subtitle colour, size
or position settings.

Credits: subtitles by the w3tu / Kuntoon translation team. A fan project, not
affiliated with CD PROJEKT RED. The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

---

## 4. modThaiLogo

**Tagline**: โลโก้ภาษาไทยในเมนูหลัก — Thai logo on the main menu (optional)

**Tags/หมวดแนะนำ**: GUI / Visuals

**คำอธิบาย (ไทย)**:

```
[b]โลโก้ภาษาไทยในเมนูหลัก (ไม่บังคับ)[/b]

เปลี่ยนโลโก้บนเมนูหลักและหน้า "กดปุ่มใดก็ได้" เป็นภาษาไทย สร้างจากไฟล์เมนู
ของเกมจริงในเวอร์ชันล่าสุดจึงเรียงสัดส่วนตรงตามต้นฉบับ
ไม่มีผลกับข้อความหรือระบบอื่น ปิดเมื่อไหร่กลับเป็นโลโก้อังกฤษทันที

ใช้คู่กับชุดแปลไทย [url=<<modThaiText URL>>]modThaiText[/url] + [url=<<modThaiFont URL>>]modThaiFont[/url]

ผลงานของแฟนเกม ไม่เกี่ยวข้องกับ CD PROJEKT RED
The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

**Description (English)**:

```
[b]Thai logo on the main menu (optional)[/b]

Replaces the logo on the main menu and the "press any key" screen with a Thai
version, rebuilt from the latest game files so it matches the original layout.
Purely cosmetic; disable it any time to return to the English logo.

Part of the Thai translation set: [url=<<modThaiText URL>>]modThaiText[/url] +
[url=<<modThaiFont URL>>]modThaiFont[/url]

A fan project, not affiliated with CD PROJEKT RED.
The Witcher 3: Wild Hunt © CD PROJEKT S.A.
```

---

## หมายเหตุการใช้งาน

- ระหว่างเป็น unlisted ไม่จำเป็นต้องใส่คำอธิบายเต็ม — ใส่ขั้นต่ำแล้วค่อยเติมตอนเปิดเผย
- หลังแต่ละหน้าผ่านอนุมัติ console ให้เพิ่มบรรทัดแรกว่า
  "พร้อมใช้บน PS5 / Xbox Series X|S / Switch 2 ผ่านเมนู Mods ในเกม"
- ตัวเลข 98% เป็นค่าประมาณจาก README — แทนที่ด้วยค่าจริงจาก build-info.json ทุกครั้งที่อัปเดต
