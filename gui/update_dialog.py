"""Update notification banner and release notes dialog."""
from __future__ import annotations

import re
import tkinter as tk
import unicodedata
import webbrowser
from tkinter import ttk

from core import __version__
from core.paths import app_data_label
from core.update import UpdateInfo
from gui.theme import P, ui

MAX_LINE_BYTES = 180  # Tk on Windows splits drawing near 200 UTF-8 bytes and detaches Thai marks there


def _wrap_bytes(line: str) -> list[str]:
    pieces = []
    while len(line.encode()) > MAX_LINE_BYTES:
        cut = end = 0
        for i, ch in enumerate(line):
            if len(line[:i + 1].encode()) > MAX_LINE_BYTES:
                break
            end = i + 1
            if ch == " ":
                cut = i
        if cut <= 0:
            cut = end
            while cut > 1 and unicodedata.category(line[cut]) == "Mn":
                cut -= 1
        pieces.append(line[:cut].rstrip())
        line = "  " + line[cut:].lstrip()
    pieces.append(line)
    return pieces


def plain_notes(text: str) -> list[tuple[str, bool]]:
    """Release markdown as (line, is_heading) with short lines that Tk can draw."""
    out = []
    for raw in text.replace("\r", "").split("\n"):
        heading = raw.lstrip().startswith("#")
        line = re.sub(r"^#+\s*", "", raw.strip()) if heading else raw.rstrip()
        line = line.replace("**", "").replace("`", "")
        out += [(piece, heading) for piece in _wrap_bytes(line)]
    return out


class UpdateBanner(tk.Frame):
    def __init__(self, parent, info: UpdateInfo):
        super().__init__(parent, bg=P.banner_bg, padx=12, pady=6)
        self.info = info
        tk.Label(self, bg=P.banner_bg, fg=P.banner_fg, font=ui(10, "bold"),
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
        notes = tk.Text(root, wrap="word", height=12, relief="solid", borderwidth=1, font=ui(10))
        notes.tag_configure("h", font=ui(10, "bold"))
        for line, heading in plain_notes(info.notes or "ไม่มีรายละเอียด"):
            notes.insert("end", line + "\n", ("h",) if heading else ())
        notes.configure(state="disabled")
        notes.grid(row=1, column=0, sticky="nsew", pady=8)
        ttk.Label(root, wraplength=500, justify="left",
                  text="วิธีอัปเดต: ดาวน์โหลด zip แล้วแตกไฟล์ทับโฟลเดอร์เดิม หรือแตกไว้ที่ใหม่ก็ได้ "
                       f"ค่าที่ตั้งไว้เก็บแยกไว้ใน {app_data_label()} จึงไม่หาย "
                       "จากนั้นเปิดโปรแกรมแล้วกดติดตั้งอีกครั้ง").grid(
            row=2, column=0, sticky="w")
        buttons = ttk.Frame(root)
        buttons.grid(row=3, column=0, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="ดาวน์โหลด", style="Big.TButton",
                   command=lambda: webbrowser.open(info.download_url)).pack(side="left")
        ttk.Button(buttons, text="ปิด", command=self.destroy).pack(side="left", padx=(4, 0))
