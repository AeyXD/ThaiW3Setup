"""Update notification banner and release notes dialog."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import ttk

from core import __version__
from core.update import UpdateInfo

BANNER_BG = "#fff4c2"


class UpdateBanner(tk.Frame):
    def __init__(self, parent, info: UpdateInfo):
        super().__init__(parent, bg=BANNER_BG, padx=12, pady=6)
        self.info = info
        tk.Label(self, bg=BANNER_BG, font=("Leelawadee UI", 10, "bold"),
                 text=f"มีโปรแกรมเวอร์ชันใหม่ v{info.version} (เครื่องนี้ใช้ v{__version__})").pack(side="left")
        ttk.Button(self, text="ปิด", command=self.destroy).pack(side="right")
        ttk.Button(self, text="ดาวน์โหลด", command=self.download).pack(side="right", padx=(0, 4))

    def download(self):
        webbrowser.open(self.info.download_url)


class UpdateDialog(tk.Toplevel):
    def __init__(self, parent, info: UpdateInfo):
        super().__init__(parent)
        self.info = info
        self.title(f"เวอร์ชันใหม่ v{info.version}")
        self.transient(parent)
        self.minsize(520, 360)
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        ttk.Label(root, style="Bold.TLabel",
                  text=f"เวอร์ชันใหม่ v{info.version}  (เครื่องนี้ใช้ v{__version__})").grid(row=0, column=0, sticky="w")
        notes = tk.Text(root, wrap="word", height=12, relief="solid", borderwidth=1, font=("Leelawadee UI", 10))
        notes.insert("1.0", info.notes or "ไม่มีรายละเอียด")
        notes.configure(state="disabled")
        notes.grid(row=1, column=0, sticky="nsew", pady=8)
        ttk.Label(root, wraplength=500, justify="left",
                  text="วิธีอัปเดต: ดาวน์โหลด zip แล้วแตกไฟล์ทับโฟลเดอร์เดิม หรือแตกไว้ที่ใหม่ก็ได้ "
                       "ค่าที่ตั้งไว้เก็บแยกไว้ใน %APPDATA% จึงไม่หาย จากนั้นเปิดโปรแกรมแล้วกดติดตั้งอีกครั้ง").grid(
            row=2, column=0, sticky="w")
        buttons = ttk.Frame(root)
        buttons.grid(row=3, column=0, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="ดาวน์โหลด", style="Big.TButton",
                   command=lambda: webbrowser.open(info.download_url)).pack(side="left")
        ttk.Button(buttons, text="ปิด", command=self.destroy).pack(side="left", padx=(4, 0))
