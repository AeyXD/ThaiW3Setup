# ThaiW3Setup — ติดตั้งภาษาไทย The Witcher 3: Wild Hunt — Remastered

โปรแกรมติดตั้ง mod แปลไทยสำหรับ **The Witcher 3: Wild Hunt — Remastered** (Steam / GOG / Epic / แอป Xbox)
ใช้คำแปลของ w3tu (Witcher 3 Translate Utility) เป็นหลัก และเติมข้อความที่ยังขาดจาก Google Sheet ของกลุ่มนักแปลอีกชุด
แล้วสร้างไฟล์ใหม่ให้ตรงกับรูปแบบของเวอร์ชัน Remastered

- ข้อความในเกมเป็นภาษาไทย (แปลแล้วประมาณ 97.8%) พร้อมฟอนต์ไทย 6 แบบ
- ซับสองภาษา ไทย + อังกฤษ เลือกได้ว่าจะให้ภาษาไหนอยู่บรรทัดแรก
- ปรับสีและขนาดซับแต่ละบรรทัดได้ และให้ชื่อผู้พูดแสดงเป็นสีได้ มีหน้าตัวอย่างที่ใช้ฟอนต์จริงของเกม
- แสดงชื่อผู้พูดหน้าซับในฉากสนทนา (เกมปกติไม่แสดง) โดยดูว่าตัวละครไหนกำลังพูดอยู่
- ย้ายตำแหน่งซับระหว่างเล่น ซับฉากสนทนา และกล่องตัวเลือกบทสนทนาได้อิสระแยกกัน และปรับความกว้างกล่องซับได้ โดยลากในภาพจำลองจอก่อนติดตั้ง (ปุ่ม ปรับตำแหน่ง...)
- ซับคัตซีน Storybook ภาษาไทย
- ตัดคำภาษาไทยอัตโนมัติ ข้อความยาวอย่าง Bestiary, journal และคำอธิบายไอเทมจะขึ้นบรรทัดใหม่ระหว่างคำได้ ไม่ต้องรอช่องว่าง บรรทัดจึงเต็มขึ้นและไม่มีช่องห่างใหญ่ ๆ ในโหมดซับสองภาษา ภาษาอังกฤษของข้อความหลายบรรทัดจะเว้นบรรทัดแยกจากภาษาไทย
- คำอธิบายในหน้าภารกิจและหน้าบันทึก (Bestiary, Encyclopedia, Storybook, หนังสือ) จัดชิดซ้ายแทนการจัดเต็มบรรทัด ช่องว่างระหว่างคำจึงไม่ถูกยืดจนห่าง และเว้นระยะบรรทัดเพิ่มให้สระและวรรณยุกต์ไม่ชนกัน
- โลโก้เกมภาษาไทยในเมนูหลักและหน้า "กดปุ่มใดก็ได้" (ไม่บังคับ ติ๊ก **โลโก้ภาษาไทยในเมนูหลัก**) สร้างจากไฟล์เมนูของเกมในเครื่องทุกครั้งที่ติดตั้ง จึงตรงกับเวอร์ชันเกมเสมอ
- ปรับแต่งคำแปลด้วย sheet เสริม (เหมือนใน w3tu) เปิด/ปิดและเรียงลำดับได้ หรือเพิ่ม sheet ของตัวเอง
- ดาวน์โหลดคำแปลล่าสุดจาก Google Sheets ของทีมแปลทุกครั้งที่ติดตั้ง ถ้าออฟไลน์จะใช้คำแปลที่มากับโปรแกรม

> รองรับเฉพาะเวอร์ชัน Remastered ถ้าเป็นเวอร์ชัน Next-Gen 4.x ให้ใช้ w3tu ตัวเดิม
> โปรแกรมดูเวอร์ชันจาก `bin\x64_dx12\witcher3.exe` (5.x = Remastered) ถ้าอัปเกมมาจาก 4.x แล้วยังมีโฟลเดอร์ `content\content1`-`content12` ค้างอยู่ จะขึ้นคำเตือนให้ลบ (ห้ามลบ `content0`)

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

### บน macOS

เกมไม่มีเวอร์ชัน macOS ถ้าเล่นบน Mac แสดงว่าไฟล์เกมอยู่ใน bottle ของ CrossOver / Whisky / Heroic / Porting Kit
โปรแกรมหา bottle ให้เอง ถ้าหาไม่เจอก็กด **เลือก...** ชี้ไปที่โฟลเดอร์เกมใน bottle ได้

1. ดาวน์โหลด `ThaiW3Setup-x.y.z-macos-arm64.zip` แล้วแตกไฟล์
2. **เปิดครั้งแรกต้องปลดล็อกก่อน** เพราะโปรแกรมยังไม่ได้ notarize กับ Apple — เปิด Terminal แล้วพิมพ์
   `xattr -dr com.apple.quarantine ` จากนั้นลากไฟล์ `ThaiW3Setup.app` มาวางต่อท้ายแล้วกด Enter
   (หรือดับเบิลคลิกให้ขึ้นคำเตือนก่อน แล้วไป System Settings > Privacy & Security กด **Open Anyway**)
3. จากนั้นใช้งานเหมือนบน Windows ทุกอย่าง

> รองรับ Mac ชิป Apple (M1 ขึ้นไป) เท่านั้น ยังไม่รองรับ Intel Mac
> ถ้าไม่ปลดล็อกตามข้อ 2 macOS จะขึ้นว่า *"Apple could not verify..."* โดยปุ่มเริ่มต้นเป็น **Move to Trash**

### สร้างไฟล์ไว้ copy เอง

ถ้ากดติดตั้งแล้วเขียนลงโฟลเดอร์เกมไม่ได้ (เช่นเกมจากแอป Xbox / Game Pass) ให้กดลูกศรข้างปุ่ม **ติดตั้ง / อัปเดต** แล้วเลือก **สร้างไฟล์ไว้ copy เอง...** แทน
แล้วเลือกที่เก็บ โปรแกรมจะสร้างโฟลเดอร์ `ThaiW3_mods` ที่มี `modThai*` ครบตามตัวเลือกที่ตั้งไว้ (ฟอนต์ ซับสองภาษา สี ขนาด ตำแหน่ง คำแปลเสริม)
พร้อมไฟล์ `วิธีติดตั้ง.txt` ให้คัดลอกโฟลเดอร์ `modThai*` ทั้งหมดไปไว้ใน `mods` ของโฟลเดอร์เกมเอง (สร้าง `mods` ถ้ายังไม่มี และลบ `modThai*` ตัวเก่าก่อน)
โปรแกรมยังต้องอ่านไฟล์ของเกมเพื่อสร้างข้อความและ script ซับ จึงต้องเลือกโฟลเดอร์เกมให้ถูกต้องเหมือนตอนติดตั้งปกติ

> เกมจากแอป Xbox อยู่ที่ `X:\XboxGames\<ชื่อเกม>\Content` โปรแกรมค้นหาให้เอง และถ้าเลือกโฟลเดอร์ชื่อเกมจะเข้าไปที่ `Content` ให้อัตโนมัติ
> เวอร์ชัน Xbox เก็บตัวเกมไว้ที่ `bin\gaming.desktop.x64` และ Windows ซ่อนไฟล์ exe ไว้ โปรแกรมจึงดูเวอร์ชันจากโครงสร้างโฟลเดอร์ `content` แทน (มีแค่ `content0` = Remastered)

## ปรับแต่งคำแปล (คำแปลเสริม)

กดปุ่ม **ปรับแต่งคำแปล...** เพื่อเลือก sheet เสริมที่จะใช้ทับคำแปลหลัก ค่าเริ่มต้นมี 5 ไฟล์จาก w3tu

| ไฟล์ | ใช้ทำอะไร | ค่าเริ่มต้น |
| --- | --- | --- |
| ข้อความที่หายไป | เติมข้อความที่ตกหล่น | เปิด |
| ชื่อเควสภาษาอังกฤษ | แสดงชื่อเควสเป็นภาษาอังกฤษ | ปิด |
| ปรับปรุงการแปล | สำนวนที่ปรับปรุงใหม่ | ปิด |
| สุภาพกันหน่อย | ลดคำหยาบ | ปิด |
| ซับนรก | คำแปลขำๆ | ปิด |
| แปลชื่อตัวละคร / แปลชื่อเมือง / แปลชื่อเควส / แปลชื่อสกิล / แปลชื่อมอนสเตอร์ / แปลชื่อไอเทม / แปลชื่อการ์ดเกวนต์ / แปลชื่ออื่นๆ | ชื่อเฉพาะแบบ อังกฤษ (ไทย) หรือไทยอย่างเดียว ถ้าปิดจะเป็นชื่ออังกฤษ | ปิด |

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

คำแปลหลักคงชื่อเฉพาะไว้เป็นภาษาอังกฤษ ถ้าอยากเห็นชื่อไทยกำกับ ให้เปิด **แปลชื่อตัวละคร**, **แปลชื่อเมือง**, **แปลชื่อเควส**, **แปลชื่อสกิล**, **แปลชื่อมอนสเตอร์**, **แปลชื่อไอเทม**, **แปลชื่อการ์ดเกวนต์** หรือ **แปลชื่ออื่นๆ** ในหน้าต่างปรับแต่งคำแปล (เปิดแยกกันได้)
ชื่อไทยมาจากแท็บชื่อเดียวกันใน [Google Sheet ชุมชน](https://docs.google.com/spreadsheets/d/1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk) ช่วยกันใส่ชื่อไทยในคอลัมน์ `THAI` แล้วคอลัมน์ `TRANSLATE` จะกลายเป็น อังกฤษ (ไทย) ให้เอง แถวที่ยังไม่มีชื่อไทยจะแสดงชื่ออังกฤษเหมือนเดิม
แท็บของแต่ละชื่อจัดตามที่เกมใช้ข้อความนั้นจริง เช่น "Triss Merigold" ในบันทึกตัวละครอยู่แท็บตัวละคร ส่วน "Triss Merigold" บนการ์ดเกวนต์อยู่แท็บการ์ดเกวนต์ ชื่อที่ระบุจากไฟล์เกมไม่ได้จะถูกเดาแท็บไว้ ถ้าอยู่ผิดแท็บ ย้ายแถวไปแท็บที่ถูกได้เลย
แต่ละรายการเลือกโหมดได้ในคอลัมน์ **โหมด**: **2 ภาษา** แสดง Yennefer (เยนเนเฟอร์) ส่วน **ไทย** แสดง เยนเนเฟอร์ อย่างเดียว ถ้าปิดรายการไหน ชื่อทุกชื่อในแท็บนั้นจะเป็นภาษาอังกฤษ แม้คำแปลหลักจะมีชื่อไทยก็ตาม

## อัปเดตตัวโปรแกรม

เมื่อเปิดโปรแกรม จะเช็กว่ามีเวอร์ชันใหม่ในหน้า Releases หรือไม่ ถ้ามีจะขึ้นแถบสีเหลืองด้านบน
กด **ดาวน์โหลด** เพื่อโหลด zip ตัวใหม่ผ่านเบราว์เซอร์ แล้วแตกไฟล์ทับโฟลเดอร์เดิมได้เลย
ค่าที่ตั้งไว้เก็บใน `%APPDATA%\ThaiW3Setup` จึงไม่หาย
popup แจ้งเตือนตอนเปิดโปรแกรมและหลังติดตั้งเสร็จ ติ๊ก **ไม่ต้องแสดงข้อความนี้อีก** เพื่อปิดถาวรได้ ถ้าอยากให้กลับมาแสดง ให้ลบ `hide_upgrade_notice_v2` / `hide_done_notice_v2` ใน `%APPDATA%\ThaiW3Setup\settings.json`

กด **ตรวจสอบอัปเดต** ที่มุมล่างซ้ายเพื่อเช็กเองและดูรายละเอียดสิ่งที่เปลี่ยน หรือใช้ `ThaiW3Setup.exe check-update`

## ถอนการติดตั้ง

กด **เพิ่มเติม** > **ถอนการติดตั้ง** ในโปรแกรม หรือลบโฟลเดอร์ `mods\modThaiText`, `mods\modThaiFont`,
`mods\modThaiStoryBook`, `mods\modThaiDoubleSub` และ `mods\modThaiLogo` ในโฟลเดอร์เกม
ถ้าอยากเอาแค่โลโก้ไทยออก ให้เอาเครื่องหมายออกจาก **โลโก้ภาษาไทยในเมนูหลัก** แล้วกดติดตั้งซ้ำ

## โปรแกรมนี้ทำอะไรกับเครื่องบ้าง

- เขียนไฟล์ลงในโฟลเดอร์ `mods\modThai*` ของเกมเท่านั้น **ไม่แก้ไขไฟล์ของตัวเกม**
  (ยกเว้นย้าย mod ไทยที่ชนกันไปไว้ที่ `mods_disabled` หลังผู้ใช้กดยืนยัน)
- เก็บค่าที่ตั้งไว้และคำแปลที่ดาวน์โหลดมาที่ `%APPDATA%\ThaiW3Setup`
- เชื่อมต่ออินเทอร์เน็ตเฉพาะเพื่อดาวน์โหลดไฟล์คำแปล (.xlsx) จาก `docs.google.com`
  และเช็กเวอร์ชันล่าสุดจาก `api.github.com` (แจ้งเตือนอย่างเดียว ไม่ดาวน์โหลดหรือรันไฟล์ใดๆ เอง)
- ไม่เขียน registry ไม่ติดตั้ง service ไม่ดาวน์โหลดโปรแกรมอื่น และไม่ขอสิทธิ์ Administrator
  (จะถามก่อนเฉพาะกรณีที่ไม่มีสิทธิ์เขียนลงโฟลเดอร์เกม)
- ถ้าพบ mod ไทยตัวเก่าของ w3tu (`modkuntoonw3thai*`) จะถามก่อนลบทุกครั้ง
- ถ้าพบ mod ภาษาไทยจากที่อื่น เช่น `modThaiLanguage` ของ ThaiLanguage Remastered (Nexus) จะถามก่อน
  แล้วย้ายไปไว้ที่โฟลเดอร์ `mods_disabled` ในโฟลเดอร์เกม (ไม่ลบ ย้ายกลับเองได้)

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

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/)

- Committers and reviewers: [FordenHillson](https://github.com/FordenHillson)
- Approvers: [FordenHillson](https://github.com/FordenHillson)

ไฟล์ที่เซ็นทุกไฟล์ build โดย GitHub Actions จากซอร์สใน repository นี้เท่านั้น และทุก release ต้องได้รับการอนุมัติก่อนเซ็น
เซ็นเฉพาะ `ThaiW3Setup.exe` ส่วนไฟล์ของ Python และ Tcl/Tk ใน `_internal` เป็นของโปรเจกต์ต้นทาง ไม่ได้เซ็นด้วยใบรับรองนี้

### Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

- ดาวน์โหลดไฟล์คำแปลจาก `docs.google.com` และเช็กเวอร์ชันล่าสุดจาก `api.github.com` โดยไม่ส่งข้อมูลของผู้ใช้ไปด้วย
- ปุ่ม **ส่งรายงานปัญหา...** ส่งข้อมูลก็ต่อเมื่อผู้ใช้กดส่งเอง ได้แก่ เวอร์ชัน Windows เกม และโปรแกรม รายชื่อ mod ที่ติดตั้ง `mods.settings`
  ส่วนท้ายของ `install.log` ข้อความและช่องทางติดต่อที่ผู้ใช้กรอก (ถ้ามี) โดยแทนชื่อผู้ใช้ Windows ในข้อมูลด้วย `<user>` ไปที่ Cloudflare Worker ของโปรเจกต์ (`worker/`) เพื่อใช้แก้ปัญหาเท่านั้น
- นโยบายของบริการที่เกี่ยวข้อง: [Google](https://policies.google.com/privacy), [GitHub](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement), [Cloudflare](https://www.cloudflare.com/privacypolicy/)

## แก้ปัญหา

| อาการ | วิธีแก้ |
| --- | --- |
| เกมขึ้น error ตอนคอมไพล์ script | มี mod อื่นแก้ไฟล์ `hudModuleDialog/Oneliners/Quests/Subtitles.ws` ซ้ำกัน ให้รวมไฟล์ด้วย Script Merger หรือเอาเครื่องหมายออกจาก "ปรับสีและขนาดซับ" แล้วติดตั้งใหม่ |
| ไม่มี "ไทย (Thai)" ในเมนูภาษา | ตรวจว่ามีโฟลเดอร์ `mods\modThaiText` และเกมเป็นเวอร์ชัน Remastered |
| ตัวอักษรไทยเป็นสี่เหลี่ยม | ตรวจว่ามี `mods\modThaiFont` และไม่มี mod ฟอนต์อื่นทับ |
| ภาษาไทยเพี้ยน/เป็นตัวเหลี่ยมหลังลง mod ไทยตัวอื่นด้วย | ห้ามใช้คู่กับ ThaiLanguage Remastered จาก Nexus (`modThaiLanguage` และ `modThaiFont` ของเขาชื่อซ้ำกับของเรา) ให้กด **ติดตั้ง / อัปเดต** อีกครั้ง โปรแกรมจะถามแล้วย้ายออกให้ |
| ข้อความเพี้ยนหลังใช้ w3tu ตัวเก่า | ใน Steam/GOG ให้ Verify integrity of game files แล้วติดตั้งใหม่ |
| เขียนลงโฟลเดอร์เกมไม่ได้ (เช่นเกมจากแอป Xbox) | กด **สร้างไฟล์ไว้ copy เอง...** แล้วคัดลอก `modThai*` ลงโฟลเดอร์ `mods` ของเกมเอง |
| ติดตั้งไม่สำเร็จ | ดู log ที่ `%APPDATA%\ThaiW3Setup\install.log` |

## ใช้งานผ่าน command line

```
ThaiW3Setup.exe detect
ThaiW3Setup.exe install --font Sarabun --mode double --color1 #FFFFFF --color2 #A0A0A0 --size2 24
ThaiW3Setup.exe install --sub-y -10 --sub-width 120 --dialog-y -8 --choice-x -10 --choice-y 5 --choice-scale 120
ThaiW3Setup.exe export --out D:\ThaiFiles --font Sarabun --mode double
ThaiW3Setup.exe status
ThaiW3Setup.exe uninstall
```

`export` ใช้ตัวเลือกเดียวกับ `install` แต่สร้างไฟล์ไว้ที่ `<out>\ThaiW3_mods` ให้คัดลอกลง `mods` ของเกมเอง

ดูตัวเลือกทั้งหมดได้จาก `ThaiW3Setup.exe install --help`

## Build จากซอร์ส

ต้องมี Python 3.10 ขึ้นไป (64-bit)

```bat
python -m pip install -r requirements.txt
python main.py            :: เปิด GUI
build.bat                 :: สร้าง dist\ThaiW3Setup-<version>.zip
build.bat offline         :: build โดยไม่ดาวน์โหลดคำแปลใหม่
```

### รันบน macOS (ทดลอง สำหรับนักพัฒนา)

เกมไม่มีเวอร์ชัน macOS โปรแกรมบน Mac จึงใช้ได้กับไฟล์เกมที่อยู่ใน bottle ของ
CrossOver / Whisky / Heroic / Porting Kit

โปรแกรมหา bottle ให้เองจากที่ตั้งมาตรฐาน (และจาก `WINEPREFIX` ถ้าตั้งไว้) แล้วอ่าน
`system.reg` / `user.reg` กับ `libraryfolders.vdf` ข้างในเพื่อหาโฟลเดอร์เกม เหมือนที่ฝั่ง Windows
อ่าน registry จริง ไดรฟ์ที่ map ไว้ใน `dosdevices/` ถูกแปลงกลับเป็น path ของ Mac ให้ด้วย
ถ้าหาไม่เจอก็กด "เลือก..." ชี้เองได้ เช่น
`~/Library/Application Support/CrossOver/Bottles/<bottle>/drive_c/Program Files (x86)/Steam/steamapps/common/The Witcher 3`

```bash
brew install python@3.12 python-tk@3.12
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py          # เปิด GUI
./build.sh                        # สร้าง dist/ThaiW3Setup-<version>-macos-<arch>.zip
./build.sh offline                # build โดยไม่ดาวน์โหลดคำแปลใหม่
```

`build.sh` ใช้ `ThaiW3Setup.spec` ตัวเดียวกับ Windows โดย spec เลือกไอคอนและ `BUNDLE()` ตาม platform
ได้ `.app` ที่มี Tcl/Tk อยู่ข้างใน ไม่ต้องมี Python ในเครื่องปลายทาง และ zip ด้วย `ditto` เพื่อไม่ให้ลายเซ็นเสีย

.app ยังไม่ได้ notarize ผู้ใช้จึงต้องปลดล็อกเองครั้งแรก (ดูหัวข้อ "บน macOS" ด้านบน)
การ notarize ต้องสมัคร Apple Developer Program ปีละ $99

ค่าที่ตั้งไว้เก็บที่ `~/Library/Application Support/ThaiW3Setup` แทน `%APPDATA%`
และสคริปต์ใน `devtools/` อ่านโฟลเดอร์เกมจากตัวแปรแวดล้อม `W3_GAME`

โครงสร้างโค้ด

- `core/w3strings.py` อ่าน/เขียนไฟล์ `.w3strings` (ทั้ง UTF-16 v162 และ UTF-8 v164 ของ Remastered)
- `core/bundle.py`, `core/metastore.py` อ่าน bundle เดิมของ w3tu และเขียน bundle v5 / `metadata.store` v7
- `core/script_patcher.py` ใส่ patch ซับสองภาษาลงบน script ของเกมเวอร์ชันที่ผู้ใช้มี
- `core/text_builder.py` รวมคำแปลเข้ากับข้อความของเกม
- `core/installer.py` ติดตั้ง / ถอนการติดตั้ง / ตรวจสถานะ
- `core/report.py` สร้างและส่งรายงานปัญหา (`worker/` คือฝั่งรับรายงาน)
- `core/pe_version.py` อ่าน version ของ `witcher3.exe` เองบนเครื่องที่ไม่มี Windows API
- `core/wine.py` หา bottle ของ Wine/CrossOver บน macOS และแปลง path ของ Windows เป็น path ของ Mac
- `gui/` หน้าต่างโปรแกรม (tkinter)

## สำหรับผู้ดูแล release

- push tag `vX.Y.Z` (หลังแก้ `__version__` ใน `core/__init__.py`) แล้ว GitHub Actions จะ build, สแกน และสร้าง Release ให้เอง
- bootloader ของ PyInstaller ถูก compile ใหม่จากซอร์สใน CI และปิด UPX เพื่อลดโอกาสที่แอนตี้ไวรัสจะตรวจผิด
- ตั้ง secret `VT_API_KEY` (API key ฟรีจาก virustotal.com) เพื่อแนบลิงก์ผลสแกน VirusTotal ในหน้า Release
- การเซ็นโค้ดผ่าน [SignPath Foundation](https://signpath.org/) (ฟรีสำหรับโอเพนซอร์ส)
  - ใน SignPath ต้องมี project slug `ThaiW3Setup`, signing policy slug `release-signing`, Trusted Build System "GitHub.com"
    และ artifact configuration ตาม `packaging/signpath/artifact-configuration.xml`
  - ตั้ง secret `SIGNPATH_API_TOKEN` และ variable `SIGNPATH_ORGANIZATION_ID` ใน GitHub แล้ว workflow จะส่งไฟล์ไปเซ็นก่อน zip ให้อัตโนมัติ
  - ทุก release ต้องกดอนุมัติใน SignPath (workflow รอได้สูงสุด 4 ชั่วโมง) แล้ว workflow จะตรวจว่า `ThaiW3Setup.exe` มีลายเซ็นถูกต้องก่อนปล่อย
  - ถ้าไม่ผ่าน ใช้ Certum Open Source Code Signing แทนได้ (เซ็นด้วย `signtool` ก่อนขั้นตอน Package)
- อัปเดตชีตข้อความที่ยังไม่แปล: `python devtools/export_untranslated.py --sheet 1kIj-WNi24iy3--NLHNzcIj5szOBXoxHJGdwRQNj0etk`
  (คำแปลและหมายเหตุที่คนใส่ไว้จะคงอยู่ ดูวิธีตั้งค่า Google OAuth ที่หัวไฟล์สคริปต์)
- อัปเดตแท็บชื่อเฉพาะ (เก็บชื่อไทยที่ใส่ไว้): `python devtools/export_names.py`
- ระบบรับรายงานปัญหา (ปุ่ม "ส่งรายงานปัญหา..." ในโปรแกรม) เป็น Cloudflare Worker + R2 อยู่ใน `worker/`
  1. `cd worker` แล้ว `npm install` และ `npx wrangler login`
  2. `npx wrangler r2 bucket create thaiw3setup-reports`
  3. `npx wrangler secret put ADMIN_PASSWORD` (รหัสผ่านเข้าหน้ารายการรายงาน)
  4. `npx wrangler deploy` แล้วใส่ URL ที่ได้ (ต่อท้ายด้วย `/report`) ใน `REPORT_URL` ของ `core/report.py`
  5. ดูรายงานที่ URL ของ Worker (ใส่ชื่อผู้ใช้อะไรก็ได้ กับรหัสผ่าน `ADMIN_PASSWORD`) หรือใน R2 บน dashboard
  - ทดสอบในเครื่อง: สร้าง `worker/.dev.vars` ที่มี `ADMIN_PASSWORD=...` แล้ว `npx wrangler dev`
    จากนั้นตั้ง `THAIW3_REPORT_URL=http://127.0.0.1:8787/report` ก่อนเปิดโปรแกรม

## เครดิต

- คำแปลภาษาไทย ฟอนต์ และซับ Storybook: ทีมแปล w3tu / Kuntoon และผู้ร่วมแปลทุกคนใน Google Sheets
- คำแปลส่วนเติม: ผู้ร่วมแปลใน [Google Sheet ของกลุ่มนักแปล The Witcher 3 ภาษาไทย](https://docs.google.com/spreadsheets/d/1Ar5MVSc4Mdr7YAFssOmTJcJ9IyHrtxUZxt649-DhnA4)
- patch ซับสองภาษาต้นฉบับ: svvv
- ภาพพื้นหลังในหน้าต่างปรับตำแหน่งซับ: MILOGAME_AVIF HDR ([อัลบั้ม Zonerama](https://eu.zonerama.com/PrestigiousCap4934/Album/16612460))
- ไอคอนปุ่ม: [Material Symbols](https://github.com/google/material-design-icons) ของ Google (Apache License 2.0) สร้างด้วย `devtools/make_ui_icons.py`
- ซอร์สโค้ดของโปรแกรมใช้ [MIT License](LICENSE) ส่วนคำแปล ฟอนต์ และภาพเป็นลิขสิทธิ์ของเจ้าของแต่ละราย
- The Witcher 3: Wild Hunt © CD PROJEKT S.A. โปรแกรมนี้เป็นผลงานของแฟนเกม ไม่เกี่ยวข้องกับ CD PROJEKT RED
