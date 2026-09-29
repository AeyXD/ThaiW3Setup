"""Dialog for choosing and ordering the custom translation sheets."""
from __future__ import annotations

import copy
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog, ttk

from core.custom import cached_count, default_sheets, download_custom, parse_sheet_id, sheet_url

ON, OFF = "☑", "☐"


class CustomSheetsDialog(tk.Toplevel):
    def __init__(self, parent, sheets: list[dict], on_save):
        super().__init__(parent)
        self.title("ตั้งค่าการแปลแบบปรับแต่ง")
        self.transient(parent)
        self.resizable(True, True)
        self.minsize(640, 360)
        self.sheets = copy.deepcopy(sheets)
        self.on_save = on_save
        self.counts = {s["sheet_id"]: cached_count(s["sheet_id"]) for s in self.sheets}
        self.events: queue.Queue = queue.Queue()
        self.busy = 0
        self._build()
        self.refresh()
        self.grab_set()
        self.after(100, self._poll)

    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        ttk.Label(root, foreground="#5b3fc4",
                  text="* ถ้าข้อความซ้ำกัน ข้อความของไฟล์ที่อยู่ข้างบนจะถูกทับด้วยข้อความจากไฟล์ที่อยู่ข้างล่าง").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        cols = ("on", "sheet", "name", "count")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse", height=8)
        for col, text, width, anchor in (("on", "เปิดใช้", 60, "center"), ("sheet", "ไฟล์ ID", 140, "w"),
                                          ("name", "คำอธิบาย", 260, "w"), ("count", "ข้อความ", 80, "e")):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=col == "name")
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
        self.status = tk.StringVar(value="คลิกช่อง เปิดใช้ เพื่อเปิด/ปิด  ดับเบิลคลิกเพื่อเปลี่ยนชื่อ")
        ttk.Label(root, textvariable=self.status).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    # ---------- list ----------
    def refresh(self, select: int | None = None):
        self.tree.delete(*self.tree.get_children())
        for i, s in enumerate(self.sheets):
            count = self.counts.get(s["sheet_id"])
            short = s["sheet_id"][:10] + "..."
            self.tree.insert("", "end", iid=str(i), values=(
                ON if s.get("enabled") else OFF, short, s.get("name") or s["sheet_id"],
                f"{count:,}" if count is not None else "-"))
        if select is not None and 0 <= select < len(self.sheets):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))

    def selected(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#1":
            row = self.tree.identify_row(event.y)
            if row:
                self.toggle(int(row))
                return "break"
        return None

    def toggle(self, index: int | None):
        if index is None:
            return
        self.sheets[index]["enabled"] = not self.sheets[index].get("enabled")
        self.refresh(index)

    def move(self, delta: int):
        i = self.selected()
        if i is None or not 0 <= i + delta < len(self.sheets):
            return
        self.sheets[i], self.sheets[i + delta] = self.sheets[i + delta], self.sheets[i]
        self.refresh(i + delta)

    def select_all(self):
        state = not all(s.get("enabled") for s in self.sheets)
        for s in self.sheets:
            s["enabled"] = state
        self.refresh(self.selected())

    def view(self):
        i = self.selected()
        if i is not None:
            webbrowser.open(sheet_url(self.sheets[i]["sheet_id"]))

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
            self.counts.update({s["sheet_id"]: cached_count(s["sheet_id"]) for s in self.sheets})
            self.refresh(0)

    # ---------- downloads ----------
    def _run(self, sheet_id: str, message: str, on_done):
        self.busy += 1
        self.status.set(message)
        self.configure(cursor="watch")

        def work():
            try:
                self.events.put((on_done, sheet_id, download_custom(sheet_id), None))
            except Exception as exc:
                self.events.put((on_done, sheet_id, None, exc))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                on_done, sheet_id, result, error = self.events.get_nowait()
                self.busy -= 1
                if self.busy == 0:
                    self.configure(cursor="")
                on_done(sheet_id, result, error)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll)

    def _updated(self, sheet_id, result, error):
        if error:
            self.status.set(f"อัปเดตไม่สำเร็จ: {error}")
            return
        _title, strings = result
        self.counts[sheet_id] = len(strings)
        self.status.set(f"อัปเดตแล้ว {len(strings):,} ข้อความ")
        self.refresh(self.selected())

    def update_selected(self):
        i = self.selected()
        if i is not None:
            self._run(self.sheets[i]["sheet_id"], "กำลังอัปเดต...", self._updated)

    def update_all(self):
        for s in self.sheets:
            self._run(s["sheet_id"], "กำลังอัปเดตทั้งหมด...", self._updated)

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
        if any(s["sheet_id"] == sheet_id for s in self.sheets):
            messagebox.showinfo("เพิ่มคำแปลเสริม", "มี sheet นี้ในรายการแล้ว", parent=self)
            return
        self._run(sheet_id, "กำลังตรวจ sheet...", self._added)

    def _added(self, sheet_id, result, error):
        if error:
            self.status.set("")
            messagebox.showerror("เพิ่มคำแปลเสริม", f"เปิด sheet ไม่ได้:\n{error}", parent=self)
            return
        title, strings = result
        self.sheets.append({"sheet_id": sheet_id, "name": title or sheet_id, "enabled": True})
        self.counts[sheet_id] = len(strings)
        self.status.set(f"เพิ่มแล้ว {len(strings):,} ข้อความ")
        self.refresh(len(self.sheets) - 1)

    def save(self):
        self.on_save(copy.deepcopy(self.sheets))
        self.destroy()
