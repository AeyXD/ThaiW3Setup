"""Dialog for choosing and ordering the custom translation sheets."""
from __future__ import annotations

import copy
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog, ttk

from core.custom import (NAME_DOUBLE, NAME_THAI, UNLOCK_CODE, cached_stats, default_sheets, download_custom,
                         hidden_sheets, is_name_tab, parse_sheet_id, progress_of, sheet_key, sheet_url)
from gui.theme import P

ON, OFF = "☑", "☐"
MODE_LABELS = {NAME_THAI: "\u0e44\u0e17\u0e22", NAME_DOUBLE: "2 \u0e20\u0e32\u0e29\u0e32"}
# dropdown entries spell out what each mode shows in game
MODE_CHOICES = {NAME_THAI: "\u0e44\u0e17\u0e22: \u0e40\u0e22\u0e19\u0e40\u0e19\u0e40\u0e1f\u0e2d\u0e23\u0e4c",
                NAME_DOUBLE: "2 \u0e20\u0e32\u0e29\u0e32: Yennefer (\u0e40\u0e22\u0e19\u0e40\u0e19\u0e40\u0e1f\u0e2d\u0e23\u0e4c)"}
MODE_HINT = ("\u0e04\u0e25\u0e34\u0e01\u0e0a\u0e48\u0e2d\u0e07 \u0e42\u0e2b\u0e21\u0e14 "
             "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e44\u0e17\u0e22/2 \u0e20\u0e32\u0e29\u0e32")


class CustomSheetsDialog(tk.Toplevel):
    def __init__(self, parent, sheets: list[dict], on_save):
        super().__init__(parent)
        self.title("ตั้งค่าการแปลแบบปรับแต่ง")
        self.transient(parent)
        self.resizable(True, True)
        self.minsize(640, 360)
        self.sheets = copy.deepcopy(sheets)
        self.on_save = on_save
        self.counts = {sheet_key(s): cached_stats(s["sheet_id"], s.get("tab") or "") for s in self.sheets}
        self.events: queue.Queue = queue.Queue()
        self.busy = 0
        self.typed = ""
        self._build()
        self.refresh()
        self.grab_set()
        self.after(100, self._poll)

    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        ttk.Label(root, foreground=P.link,
                  text="* ถ้าข้อความซ้ำกัน ข้อความของไฟล์ที่อยู่ข้างบนจะถูกทับด้วยข้อความจากไฟล์ที่อยู่ข้างล่าง").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        cols = ("on", "sheet", "name", "mode", "count", "percent")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse", height=8)
        for col, text, width, anchor in (("on", "เปิดใช้", 60, "center"), ("sheet", "ไฟล์ ID", 140, "w"),
                                          ("name", "คำอธิบาย", 260, "w"), ("count", "ข้อความ", 80, "e"),
                                          ("percent", "แปลแล้ว", 70, "e")):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=col == "name")
        self.tree.heading("mode", text="\u0e42\u0e2b\u0e21\u0e14")
        self.tree.column("mode", width=80, anchor="center", stretch=False)
        self.mode_editor: ttk.Combobox | None = None
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<space>", lambda _e: self.toggle(self.selected()))
        self.tree.bind("<Double-1>", lambda _e: self.rename())

        side = ttk.Frame(root)
        side.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        ttk.Button(side, text="เลื่อนขึ้น", command=lambda: self.move(-1)).pack(fill="x")
        ttk.Button(side, text="เลื่อนลง", command=lambda: self.move(1)).pack(fill="x", pady=(4, 0))
        ttk.Button(side, text="ดู", command=self.view).pack(fill="x", pady=(16, 0))
        ttk.Button(side, text="อัปเดต", command=self.update_selected).pack(fill="x", pady=(4, 0))
        ttk.Button(side, text="เปลี่ยนชื่อ", command=self.rename).pack(fill="x", pady=(4, 0))
        ttk.Button(side, text="บันทึก", style="Big.TButton", command=self.save).pack(side="bottom", fill="x")

        bottom = ttk.Frame(root)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(bottom, text="เพิ่ม...", command=self.add).pack(side="left")
        ttk.Button(bottom, text="ลบ", command=self.remove).pack(side="left", padx=(4, 0))
        ttk.Button(bottom, text="คืนค่าเริ่มต้น", command=self.reset).pack(side="left", padx=(4, 0))
        ttk.Button(bottom, text="ยกเลิก", command=self.destroy).pack(side="right")
        ttk.Button(bottom, text="อัปเดตทั้งหมด", command=self.update_all).pack(side="right", padx=(0, 4))
        ttk.Button(bottom, text="เลือกทั้งหมด", command=self.select_all).pack(side="right", padx=(0, 4))
        self.status = tk.StringVar(value=MODE_HINT + "  " + "คลิกช่อง เปิดใช้ เพื่อเปิด/ปิด  ดับเบิลคลิกเพื่อเปลี่ยนชื่อ")
        ttk.Label(root, textvariable=self.status).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.bind("<Key>", self._on_key, add="+")

    # ---------- list ----------
    def refresh(self, select: int | None = None):
        self._close_mode_editor()
        self.tree.delete(*self.tree.get_children())
        for i, s in enumerate(self.sheets):
            count, percent = self.counts.get(sheet_key(s), (None, None))
            short = s["sheet_id"][:10] + "..." + (f" / {s['tab']}" if s.get("tab") else "")
            self.tree.insert("", "end", iid=str(i), values=(
                ON if s.get("enabled") else OFF, short, s.get("name") or s["sheet_id"],
                MODE_LABELS.get(s.get("name_mode") or NAME_DOUBLE, "") + " ▾" if is_name_tab(s) else "",
                f"{count:,}" if count is not None else "-",
                f"{percent:.0%}" if percent is not None else "-"))
        if select is not None and 0 <= select < len(self.sheets):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))

    def selected(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_click(self, event):
        self._close_mode_editor()
        if self.tree.identify_region(event.x, event.y) != "cell":
            return None
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if row and column == "#1":
            self.toggle(int(row))
            return "break"
        if row and column == "#4" and is_name_tab(self.sheets[int(row)]):
            self.tree.selection_set(row)
            self.edit_mode(int(row))
            return "break"
        return None

    def toggle(self, index: int | None):
        if index is None:
            return
        self.sheets[index]["enabled"] = not self.sheets[index].get("enabled")
        self.refresh(index)

    def edit_mode(self, index: int):
        """Drop-down over the mode cell of a name tab."""
        bbox = self.tree.bbox(str(index), "mode")
        if not bbox:
            return
        x, y, width, height = bbox
        s = self.sheets[index]
        combo = ttk.Combobox(self.tree, values=list(MODE_CHOICES.values()), state="readonly", width=24)
        combo.set(MODE_CHOICES[s.get("name_mode") or NAME_DOUBLE])
        combo.place(x=x, y=y, height=height)
        self.mode_editor = combo

        def chosen(_event):
            s["name_mode"] = next(k for k, v in MODE_CHOICES.items() if v == combo.get())
            self.refresh(index)

        combo.bind("<<ComboboxSelected>>", chosen)
        combo.bind("<Escape>", lambda _e: self._close_mode_editor())
        combo.focus_set()
        combo.after(50, lambda: combo.winfo_exists() and combo.event_generate("<Down>"))

    def _close_mode_editor(self):
        if self.mode_editor is not None:
            self.mode_editor.destroy()
            self.mode_editor = None

    def move(self, delta: int):
        i = self.selected()
        if i is None or not 0 <= i + delta < len(self.sheets):
            return
        self.sheets[i], self.sheets[i + delta] = self.sheets[i + delta], self.sheets[i]
        self.refresh(i + delta)

    def _on_key(self, event):
        # Windows virtual-key codes for 0-9 and A-Z match ASCII, so the code works under a Thai layout too
        char = chr(event.keycode).lower() if 48 <= event.keycode <= 90 else event.char.lower()
        if not char:
            return
        self.typed = (self.typed + char)[-len(UNLOCK_CODE):]
        if self.typed == UNLOCK_CODE:
            self.typed = ""
            self.unlock_hidden()

    def unlock_hidden(self):
        have = {sheet_key(s) for s in self.sheets}
        new = [s for s in hidden_sheets() if sheet_key(s) not in have]
        if not new:
            self.status.set("\u0e04\u0e33\u0e41\u0e1b\u0e25\u0e23\u0e2d\u0e1b\u0e25\u0e48\u0e2d\u0e22\u0e2d\u0e22\u0e39\u0e48\u0e43\u0e19\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e41\u0e25\u0e49\u0e27")
            return
        self.sheets.extend(new)
        self.refresh(len(self.sheets) - 1)
        self._run(new, "\u0e1b\u0e25\u0e14\u0e25\u0e47\u0e2d\u0e01\u0e04\u0e33\u0e41\u0e1b\u0e25\u0e23\u0e2d\u0e1b\u0e25\u0e48\u0e2d\u0e22\u0e41\u0e25\u0e49\u0e27 \u0e01\u0e33\u0e25\u0e31\u0e07\u0e42\u0e2b\u0e25\u0e14...", self._updated)

    def select_all(self):
        state = not all(s.get("enabled") for s in self.sheets)
        for s in self.sheets:
            s["enabled"] = state
        self.refresh(self.selected())

    def view(self):
        i = self.selected()
        if i is not None:
            webbrowser.open(sheet_url(self.sheets[i]["sheet_id"], self.sheets[i].get("gid")))

    def rename(self):
        i = self.selected()
        if i is None:
            return
        name = simpledialog.askstring("เปลี่ยนชื่อ", "คำอธิบาย:", parent=self,
                                      initialvalue=self.sheets[i].get("name", ""))
        if name is not None:
            self.sheets[i]["name"] = name.strip()
            self.refresh(i)

    def remove(self):
        i = self.selected()
        if i is None:
            return
        name = self.sheets[i].get("name") or self.sheets[i]["sheet_id"]
        if messagebox.askyesno("ลบ", f"ลบ \"{name}\" ออกจากรายการหรือไม่?", parent=self):
            del self.sheets[i]
            self.refresh(min(i, len(self.sheets) - 1))

    def reset(self):
        if messagebox.askyesno("คืนค่าเริ่มต้น", "คืนรายการคำแปลเสริมเป็นค่าเริ่มต้นหรือไม่?", parent=self):
            self.sheets = default_sheets()
            self.counts.update({sheet_key(s): cached_stats(s["sheet_id"], s.get("tab") or "")
                                for s in self.sheets})
            self.refresh(0)

    # ---------- downloads ----------
    def _run(self, sheets: list[dict], message: str, on_done):
        """Download in one thread so tabs of the same sheet share a single download."""
        self.busy += len(sheets)
        self.status.set(message)
        self.configure(cursor="watch")
        sheets = copy.deepcopy(sheets)

        def work():
            pool: dict[str, bytes] = {}
            for s in sheets:
                try:
                    result = download_custom(s["sheet_id"], s.get("tab") or "", pool=pool)
                    self.events.put((on_done, s, result, None))
                except Exception as exc:
                    self.events.put((on_done, s, None, exc))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                on_done, sheet, result, error = self.events.get_nowait()
                self.busy -= 1
                if self.busy == 0:
                    self.configure(cursor="")
                on_done(sheet, result, error)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll)

    def _updated(self, sheet, result, error):
        if error:
            self.status.set(f"อัปเดตไม่สำเร็จ: {error}")
            return
        strings = result.strings
        self.counts[sheet_key(sheet)] = len(strings), progress_of(result)
        self.status.set(f"อัปเดตแล้ว {len(strings):,} ข้อความ")
        self.refresh(self.selected())

    def update_selected(self):
        i = self.selected()
        if i is not None:
            self._run([self.sheets[i]], "กำลังอัปเดต...", self._updated)

    def update_all(self):
        if self.sheets:
            self._run(self.sheets, "กำลังอัปเดตทั้งหมด...", self._updated)

    def add(self):
        text = simpledialog.askstring(
            "เพิ่มคำแปลเสริม",
            "วางลิงก์หรือ ID ของ Google Sheet\n(แท็บแรกต้องมีหัวตาราง ID และ TRANSLATE แบบเดียวกับ w3tu\n"
            "และต้องตั้งแชร์เป็น \"ทุกคนที่มีลิงก์\")", parent=self)
        if not text:
            return
        sheet_id = parse_sheet_id(text)
        if not sheet_id:
            messagebox.showerror("เพิ่มคำแปลเสริม", "ลิงก์หรือ ID ไม่ถูกต้อง", parent=self)
            return
        if any(sheet_key(s) == sheet_id for s in self.sheets):
            messagebox.showinfo("เพิ่มคำแปลเสริม", "มี sheet นี้ในรายการแล้ว", parent=self)
            return
        self._run([{"sheet_id": sheet_id}], "กำลังตรวจ sheet...", self._added)

    def _added(self, sheet, result, error):
        sheet_id = sheet["sheet_id"]
        if error:
            self.status.set("")
            messagebox.showerror("เพิ่มคำแปลเสริม", f"เปิด sheet ไม่ได้:\n{error}", parent=self)
            return
        title, strings = result.title, result.strings
        self.sheets.append({"sheet_id": sheet_id, "name": title or sheet_id, "enabled": True})
        self.counts[sheet_id] = len(strings), progress_of(result)
        self.status.set(f"เพิ่มแล้ว {len(strings):,} ข้อความ")
        self.refresh(len(self.sheets) - 1)

    def save(self):
        self.on_save(copy.deepcopy(self.sheets))
        self.destroy()
