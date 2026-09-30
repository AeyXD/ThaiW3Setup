# ThaiW3Setup — ติดตั้งภาษาไทย The Witcher 3: Wild Hunt — Remastered

โปรแกรมติดตั้ง mod แปลไทยสำหรับ **The Witcher 3: Wild Hunt — Remastered** (Steam / GOG / Epic)
ใช้คำแปลของ w3tu (Witcher 3 Translate Utility) เป็นหลัก และเติมข้อความที่ยังขาดจาก Google Sheet ของกลุ่มนักแปลอีกชุด
แล้วสร้างไฟล์ใหม่ให้ตรงกับรูปแบบของเวอร์ชัน Remastered

- ข้อความในเกมเป็นภาษาไทย (แปลแล้วประมาณ 97.8%) พร้อมฟอนต์ไทย 6 แบบ
- ซับสองภาษา ไทย + อังกฤษ เลือกได้ว่าจะให้ภาษาไหนอยู่บรรทัดแรก
- ปรับสีและขนาดซับแต่ละบรรทัดได้ และให้ชื่อผู้พูดแสดงเป็นสีได้ มีหน้าตัวอย่างที่ใช้ฟอนต์จริงของเกม
- ย้ายตำแหน่งซับระหว่างเล่น ซับฉากสนทนา และกล่องตัวเลือกบทสนทนาได้อิสระแยกกัน และปรับความกว้างกล่องซับได้ โดยลากในภาพจำลองจอก่อนติดตั้ง (ปุ่ม ปรับตำแหน่ง...)
- ซับคัตซีน Storybook ภาษาไทย
- ปรับแต่งคำแปลด้วย sheet เสริม (เหมือนใน w3tu) เปิด/ปิดและเรียงลำดับได้ หรือเพิ่ม sheet ของตัวเอง
- ดาวน์โหลดคำแปลล่าสุดจาก Google Sheets ของทีมแปลทุกครั้งที่ติดตั้ง ถ้าออฟไลน์จะใช้คำแปลที่มากับโปรแกรม

> รองรับเฉพาะเวอร์ชัน Remastered ถ้าเป็นเวอร์ชัน Next-Gen 4.x ให้ใช้ w3tu ตัวเดิม

## วิธีติดตั้ง

1. ดาวน์โหลด `ThaiW3Setup-x.y.z.zip` จากหน้า Releases แล้วแตกไฟล์ออกมาทั้งโฟลเดอร์ (อย่าเปิดจากในไฟล์ zip)
2. เปิด `ThaiW3Setup.exe`
3. โปรแกรมจะหาโฟลเดอร์เกมให้เอง ถ้าหาไม่เจอให้กด **เลือก...** แล้วเลือกโฟลเดอร์ที่มี `bin` และ `content`
4. เลือกฟอนต์ โหมดซับ สี และขนาดตามที่ชอบ ดูหน้าตาได้ที่กรอบตัวอย่าง
5. กด **ติดตั้ง / อัปเดต**
6. เข้าเกม ไปที่ **Options > Language > Text Language** แล้วเลือก **ไทย (Thai)**
   (ถ้าเลือกโหมด "แทนภาษาอังกฤษ" ให้ตั้งภาษาข้อความเป็น English)

ถ้าอยากเปลี่ยนฟอนต์ สี หรือขนาดภายหลัง ให้เปิดโปรแกรม ปรับค่า แล้วกดติดตั้งซ้ำ
เมื่อเกมอัปเดตหรือทีมแปลอัปเดตคำแปลแล้ว ก็กดติดตั้งซ้ำได้เช่นกัน

## ปรับแต่งคำแปล (คำแปลเสริม)

กดปุ่ม **ปรับแต่งคำแปล...** เพื่อเลือก sheet เสริมที่จะใช้ทับคำแปลหลัก ค่าเริ่มต้นมี 5 ไฟล์จาก w3tu

| ไฟล์ | ใช้ทำอะไร | ค่าเริ่มต้น |
| --- | --- | --- |
| ข้อความที่หายไป | เติมข้อความที่ตกหล่น | เปิด |
| ชื่อเควสภาษาอังกฤษ | แสดงชื่อเควสเป็นภาษาอังกฤษ | ปิด |
| ปรับปรุงการแปล | สำนวนที่ปรับปรุงใหม่ | ปิด |
| สุภาพกันหน่อย | ลดคำหยาบ | ปิด |
| ซับนรก | คำแปลขำๆ | ปิด |
| ชื่อตัวละคร / ชื่อเมือง / ชื่อเควส / ชื่อสกิล | ชื่อเฉพาะแบบ อังกฤษ (ไทย) เช่น Yennefer (เยนเนเฟอร์) | ปิด |

- ถ้าข้อความซ้ำกัน ไฟล์ที่อยู่ล่างกว่าจะทับไฟล์ที่อยู่บน ใช้ปุ่ม **เลื่อนขึ้น/เลื่อนลง** จัดลำดับ
- **เพิ่ม...** ใส่ลิงก์ Google Sheet ของตัวเองได้ แท็บแรกต้องมีหัวตาราง `ID` และ `TRANSLATE`
  (รูปแบบเดียวกับ sheet ของ w3tu) และตั้งแชร์เป็น "ทุกคนที่มีลิงก์"
- กด **บันทึก** แล้วกด **ติดตั้ง / อัปเดต** อีกครั้งเพื่อให้มีผลในเกม
- command line: `ThaiW3Setup.exe custom` ดูรายการ และ `ThaiW3Setup.exe install --custom 1,3` เลือกไฟล์ที่จะเปิด

## ช่วยแปลข้อความที่ยังไม่แปล

ข้อความในเกมที่ยังไม่มีคำแปลไทยรวมไว้ใน [Google Sheet ข้อความที่ยังไม่แปล](https://docs.google.com/spreadsheets/d/1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk)
ใส่คำแปลในคอลัมน์ `TRANSLATE` (ถ้าไม่แน่ใจความหมาย เขียนหมายเหตุในคอลัมน์ `NOTE` หรือกด comment ได้)
ชีตนี้เปิดใช้เป็นคำแปลเพิ่มเติมในโปรแกรมอยู่แล้ว คำแปลที่ใส่จะมีผลเมื่อกด **ติดตั้ง / อัปเดต** ครั้งถัดไป

## ชื่อเฉพาะแบบ อังกฤษ (ไทย)

คำแปลหลักคงชื่อตัวละคร เมือง เควส และสกิลไว้เป็นภาษาอังกฤษ ถ้าอยากเห็นชื่อไทยกำกับ ให้เปิด **ชื่อตัวละคร**, **ชื่อเมือง**, **ชื่อเควส** หรือ **ชื่อสกิล** ในหน้าต่างปรับแต่งคำแปล (เปิดแยกกันได้)
ชื่อไทยมาจากแท็บชื่อเดียวกันใน [Google Sheet ชุมชน](https://docs.google.com/spreadsheets/d/1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk) ช่วยกันใส่ชื่อไทยในคอลัมน์ `THAI` แล้วคอลัมน์ `TRANSLATE` จะกลายเป็น อังกฤษ (ไทย) ให้เอง แถวที่ยังไม่มีชื่อไทยจะแสดงชื่ออังกฤษเหมือนเดิม
ถ้าชื่อไหนอยู่ผิดแท็บ ย้ายแถวไปแท็บที่ถูกได้เลย

## อัปเดตตัวโปรแกรม

เมื่อเปิดโปรแกรม จะเช็กว่ามีเวอร์ชันใหม่ในหน้า Releases หรือไม่ ถ้ามีจะขึ้นแถบสีเหลืองด้านบน
กด **ดาวน์โหลด** เพื่อโหลด zip ตัวใหม่ผ่านเบราว์เซอร์ แล้วแตกไฟล์ทับโฟลเดอร์เดิมได้เลย
ค่าที่ตั้งไว้เก็บใน `%APPDATA%\ThaiW3Setup` จึงไม่หาย
popup แจ้งเตือนตอนเปิดโปรแกรมและหลังติดตั้งเสร็จ ติ๊ก **ไม่ต้องแสดงข้อความนี้อีก** เพื่อปิดถาวรได้ ถ้าอยากให้กลับมาแสดง ให้ลบ `hide_upgrade_notice` / `hide_done_notice` ใน `%APPDATA%\ThaiW3Setup\settings.json`

กด **ตรวจสอบอัปเดต** ที่มุมล่างซ้ายเพื่อเช็กเองและดูรายละเอียดสิ่งที่เปลี่ยน หรือใช้ `ThaiW3Setup.exe check-update`

## ถอนการติดตั้ง

กดปุ่ม **ถอนการติดตั้ง** ในโปรแกรม หรือลบโฟลเดอร์ `mods\modThaiText`, `mods\modThaiFont`,
`mods\modThaiStoryBook` และ `mods\modThaiDoubleSub` ในโฟลเดอร์เกม

## โปรแกรมนี้ทำอะไรกับเครื่องบ้าง

- เขียนไฟล์ลงในโฟลเดอร์ `mods\modThai*` ของเกมเท่านั้น **ไม่แก้ไขไฟล์ของตัวเกม**
- เก็บค่าที่ตั้งไว้และคำแปลที่ดาวน์โหลดมาที่ `%APPDATA%\ThaiW3Setup`
- เชื่อมต่ออินเทอร์เน็ตเฉพาะเพื่อดาวน์โหลดไฟล์คำแปล (.xlsx) จาก `docs.google.com`
  และเช็กเวอร์ชันล่าสุดจาก `api.github.com` (แจ้งเตือนอย่างเดียว ไม่ดาวน์โหลดหรือรันไฟล์ใดๆ เอง)
- ไม่เขียน registry ไม่ติดตั้ง service ไม่ดาวน์โหลดโปรแกรมอื่น และไม่ขอสิทธิ์ Administrator
  (จะถามก่อนเฉพาะกรณีที่ไม่มีสิทธิ์เขียนลงโฟลเดอร์เกม)
- ถ้าพบ mod ไทยตัวเก่าของ w3tu (`modkuntoonw3thai*`) จะถามก่อนลบทุกครั้ง

## Windows SmartScreen / แอนตี้ไวรัสเตือน

โปรแกรมนี้เป็นโอเพนซอร์ส build ด้วย GitHub Actions จากซอร์สในหน้านี้โดยตรง แต่เป็นโปรแกรมใหม่ที่คนดาวน์โหลดยังไม่มาก
Windows จึงอาจขึ้นเตือนได้

- **SmartScreen ("Windows protected your PC")**: กด **More info** แล้วกด **Run anyway**
- **ตรวจว่าไฟล์เป็นตัวจริง**: เทียบค่า SHA256 กับที่แจ้งในหน้า Release
  ```powershell
  Get-FileHash .\ThaiW3Setup-0.1.0.zip -Algorithm SHA256
  ```
  ในหน้า Release มีลิงก์ผลสแกนจาก VirusTotal ของไฟล์ชุดเดียวกันด้วย
- **Windows Defender แจ้งว่าเป็นไวรัส**: เป็นการตรวจผิดพลาด (false positive) ที่พบบ่อยกับโปรแกรมที่สร้างด้วย PyInstaller
  ช่วยแจ้ง Microsoft ได้ที่ <https://www.microsoft.com/en-us/wdsi/filesubmission>
  (เลือก "Software developer" หรือ "Home customer" > Incorrectly detected as malware)
  เมื่อ Microsoft ตรวจแล้วจะหายเตือนสำหรับทุกคน
- ถ้าไม่สบายใจ สามารถรันจากซอร์สโค้ดได้เอง (ดูหัวข้อด้านล่าง)

## แก้ปัญหา

| อาการ | วิธีแก้ |
| --- | --- |
| เกมขึ้น error ตอนคอมไพล์ script | มี mod อื่นแก้ไฟล์ `hudModuleDialog/Oneliners/Quests/Subtitles.ws` ซ้ำกัน ให้รวมไฟล์ด้วย Script Merger หรือเอาเครื่องหมายออกจาก "ปรับสีและขนาดซับ" แล้วติดตั้งใหม่ |
| ไม่มี "ไทย (Thai)" ในเมนูภาษา | ตรวจว่ามีโฟลเดอร์ `mods\modThaiText` และเกมเป็นเวอร์ชัน Remastered |
| ตัวอักษรไทยเป็นสี่เหลี่ยม | ตรวจว่ามี `mods\modThaiFont` และไม่มี mod ฟอนต์อื่นทับ |
| ข้อความเพี้ยนหลังใช้ w3tu ตัวเก่า | ใน Steam/GOG ให้ Verify integrity of game files แล้วติดตั้งใหม่ |
| ติดตั้งไม่สำเร็จ | ดู log ที่ `%APPDATA%\ThaiW3Setup\install.log` |

## ใช้งานผ่าน command line

```
ThaiW3Setup.exe detect
ThaiW3Setup.exe install --font Sarabun --mode double --color1 #FFFFFF --color2 #A0A0A0 --size2 24
ThaiW3Setup.exe install --sub-y -10 --sub-width 120 --dialog-y -8 --choice-x -10 --choice-y 5 --choice-scale 120
ThaiW3Setup.exe status
ThaiW3Setup.exe uninstall
```

ดูตัวเลือกทั้งหมดได้จาก `ThaiW3Setup.exe install --help`

## Build จากซอร์ส

ต้องมี Python 3.10 ขึ้นไป (64-bit)

```bat
python -m pip install -r requirements.txt
python main.py            :: เปิด GUI
build.bat                 :: สร้าง dist\ThaiW3Setup-<version>.zip
build.bat offline         :: build โดยไม่ดาวน์โหลดคำแปลใหม่
```

โครงสร้างโค้ด

- `core/w3strings.py` อ่าน/เขียนไฟล์ `.w3strings` (ทั้ง UTF-16 v162 และ UTF-8 v164 ของ Remastered)
- `core/bundle.py`, `core/metastore.py` อ่าน bundle เดิมของ w3tu และเขียน bundle v5 / `metadata.store` v7
- `core/script_patcher.py` ใส่ patch ซับสองภาษาลงบน script ของเกมเวอร์ชันที่ผู้ใช้มี
- `core/text_builder.py` รวมคำแปลเข้ากับข้อความของเกม
- `core/installer.py` ติดตั้ง / ถอนการติดตั้ง / ตรวจสถานะ
- `gui/` หน้าต่างโปรแกรม (tkinter)

## สำหรับผู้ดูแล release

- push tag `vX.Y.Z` (หลังแก้ `__version__` ใน `core/__init__.py`) แล้ว GitHub Actions จะ build, สแกน และสร้าง Release ให้เอง
- bootloader ของ PyInstaller ถูก compile ใหม่จากซอร์สใน CI และปิด UPX เพื่อลดโอกาสที่แอนตี้ไวรัสจะตรวจผิด
- ตั้ง secret `VT_API_KEY` (API key ฟรีจาก virustotal.com) เพื่อแนบลิงก์ผลสแกน VirusTotal ในหน้า Release
- การเซ็นโค้ด: สมัคร [SignPath Foundation](https://signpath.org/) (ฟรีสำหรับโอเพนซอร์ส) แล้วตั้ง secret `SIGNPATH_API_TOKEN`
  และ variable `SIGNPATH_ORGANIZATION_ID` workflow จะส่งไฟล์ไปเซ็นก่อน zip ให้อัตโนมัติ
  ถ้าไม่ผ่าน ใช้ Certum Open Source Code Signing แทนได้ (เซ็นด้วย `signtool` ก่อนขั้นตอน Package)
- อัปเดตชีตข้อความที่ยังไม่แปล: `python devtools/export_untranslated.py --sheet 1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk`
  (คำแปลและหมายเหตุที่คนใส่ไว้จะคงอยู่ ดูวิธีตั้งค่า Google OAuth ที่หัวไฟล์สคริปต์)
- อัปเดตแท็บชื่อเฉพาะ (เก็บชื่อไทยที่ใส่ไว้): `python devtools/export_names.py`

## เครดิต

- คำแปลภาษาไทย ฟอนต์ และซับ Storybook: ทีมแปล w3tu / Kuntoon และผู้ร่วมแปลทุกคนใน Google Sheets
- คำแปลส่วนเติม: ผู้ร่วมแปลใน [Google Sheet ของกลุ่มนักแปล The Witcher 3 ภาษาไทย](https://docs.google.com/spreadsheets/d/1Ar5MVSc4Mdr7YAFssOmTJcJ9IyHrtxUZxt649-DhnA4)
- patch ซับสองภาษาต้นฉบับ: svvv
- ภาพพื้นหลังในหน้าต่างปรับตำแหน่งซับ: MILOGAME_AVIF HDR ([อัลบั้ม Zonerama](https://eu.zonerama.com/PrestigiousCap4934/Album/16612460))
- The Witcher 3: Wild Hunt © CD PROJEKT S.A. โปรแกรมนี้เป็นผลงานของแฟนเกม ไม่เกี่ยวข้องกับ CD PROJEKT RED
