"""Simple toggles for Thai patches of other UI mods."""
from __future__ import annotations

import webbrowser
import tkinter as tk
from tkinter import ttk

from core.compat import COMPAT_MODS, CompatMod, MISSING, OK, PatchStatus
from gui.theme import ui
from gui.widgets import Tooltip, ttk_image

T_TAB = "ใช้ร่วมกับ mod อื่น"
T_HINT = "แพตช์แปลและใส่อักษรไทยให้ mod หน้าตาเมนู เปิดสวิตช์แล้วกดติดตั้ง / อัปเดต"
T_SWITCH = "ติดตั้งแพตช์ไปพร้อมภาษาไทย"
T_HOW = "วิธีติดตั้ง"
T_HOW_TITLE = "วิธีติดตั้ง {label}"
T_HOW_INTRO = "ใช้แพตช์ภาษาไทยกับ {label} ผ่านโปรแกรมนี้:"
T_HOW_ZIP = ("ถ้าจะ copy / ใช้ Mod Manager เอง: เปิดสวิตช์แล้วเลือก "
             "«สร้างไฟล์ไว้ copy เอง» หรือ «สร้างไฟล์ zip ไว้ copy เอง» จากเมนู ▼ ข้างปุ่มติดตั้ง")
T_OK = "ตกลง"
T_OPEN_NEXUS = "เปิดหน้า Nexus Mods"
T_HOOD_NOTE = ("รองรับ mod hood จาก nexus mod แต่ต้องตั้ง priority load order ให้มากกว่า "
               "mod ไทย และ ink and iron")
ICON_SIZE = 18


def show_install_guide(parent, mod: CompatMod, status: PatchStatus | None = None):
    """Modal popup with numbered install steps for one UI mod."""
    dlg = tk.Toplevel(parent)
    dlg.title(T_HOW_TITLE.format(label=mod.label))
    dlg.transient(parent)
    dlg.resizable(False, False)

    root = ttk.Frame(dlg, padding=16)
    root.pack(fill="both", expand=True)

    ttk.Label(root, text=T_HOW_INTRO.format(label=mod.label), wraplength=460, justify="left").pack(anchor="w")

    steps = ttk.Frame(root, padding=(0, 12, 0, 0))
    steps.pack(anchor="w", fill="x")
    current = status.step() if status is not None else None
    for i, step in enumerate(mod.direct_steps):
        active = current == i
        mark = "▶" if active else f"{i + 1}."
        style = "Bold.TLabel" if active else "TLabel"
        row = ttk.Frame(steps)
        row.pack(anchor="w", fill="x", pady=3)
        ttk.Label(row, text=mark, width=3, style=style).pack(side="left", anchor="n")
        ttk.Label(row, text=step.text, wraplength=420, justify="left", style=style).pack(
            side="left", anchor="w")

    ttk.Label(root, text=T_HOW_ZIP, wraplength=460, justify="left", style="Sub.TLabel").pack(
        anchor="w", pady=(12, 0))

    ok = ttk.Button(root, text=T_OK, command=dlg.destroy)
    ok.pack(anchor="e", pady=(14, 0))
    dlg.bind("<Return>", lambda _e: dlg.destroy())
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
    dlg.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dlg.winfo_reqwidth()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dlg.winfo_reqheight()) // 3
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    ok.focus_set()
    dlg.grab_set()
    parent.wait_window(dlg)


class CompatTab:
    """A short list of mods with an on/off switch each; no install-method copy."""

    def __init__(self, notebook: ttk.Notebook, enabled: dict[str, tk.BooleanVar], on_toggle):
        self.notebook = notebook
        self.enabled = enabled
        self.on_toggle = on_toggle
        self.statuses: dict[str, PatchStatus] = {}
        self._link_images: list = []  # keep PhotoImage refs alive
        self._hood_note: ttk.Label | None = None

        self.tab = ttk.Frame(notebook, padding=12)
        self.tab.columnconfigure(0, weight=1)
        notebook.add(self.tab, text=T_TAB)

        self.hint = ttk.Label(self.tab, text=T_HINT, justify="left", wraplength=640, style="Sub.TLabel")
        self.hint.grid(row=0, column=0, sticky="ew")

        self.list = ttk.Frame(self.tab, padding=(0, 10, 0, 0))
        self.list.grid(row=1, column=0, sticky="new")
        self.list.columnconfigure(1, weight=1)

        grid_row = 0
        for i, mod in enumerate(COMPAT_MODS.values(), start=1):
            ttk.Label(self.list, text=f"{i}.").grid(row=grid_row, column=0, sticky="w", padx=(0, 10), pady=(8, 2))
            name_row = ttk.Frame(self.list)
            name_row.grid(row=grid_row, column=1, sticky="w", pady=(8, 2))
            ttk.Label(name_row, text=mod.label, style="Bold.TLabel").pack(side="left")
            image = ttk_image(self.tab, "open_in_new", ICON_SIZE)
            self._link_images.append(image)
            link = ttk.Button(name_row, image=image, text="" if image else "↗", style="Icon.TButton",
                              command=lambda u=mod.url: webbrowser.open(u))
            link.pack(side="left", padx=(6, 0))
            Tooltip(link, T_OPEN_NEXUS)
            ttk.Button(self.list, text=T_HOW, command=lambda m=mod: self._show_guide(m)).grid(
                row=grid_row, column=2, sticky="e", padx=(12, 0), pady=(8, 2))
            sw = ttk.Checkbutton(self.list, text="", variable=enabled[mod.key], style="Switch.TCheckbutton",
                                 command=on_toggle)
            sw.grid(row=grid_row, column=3, sticky="e", padx=(10, 0), pady=(8, 2))
            Tooltip(sw, T_SWITCH)
            grid_row += 1
            if mod.key == "inkandiron":
                self._hood_note = ttk.Label(self.list, text=T_HOOD_NOTE, justify="left", wraplength=640,
                                            style="Bad.TLabel", font=ui(10, "bold"))
                self._hood_note.grid(row=grid_row, column=1, columnspan=3, sticky="ew", pady=(0, 8))
                grid_row += 1

        self.tab.bind("<Configure>", self._on_resize)
        self.refresh_tab_title()

    def _on_resize(self, event):
        wrap = max(200, event.width - 48)
        self.hint.configure(wraplength=wrap)
        if self._hood_note is not None:
            self._hood_note.configure(wraplength=max(200, event.width - 80))

    def _show_guide(self, mod: CompatMod):
        show_install_guide(self.tab.winfo_toplevel(), mod, self.statuses.get(mod.key))

    def set_sources(self, _sources: dict[str, str]):
        pass

    def set_busy(self, _busy: bool):
        pass

    def update(self, statuses: list[PatchStatus] | None = None):
        if statuses is not None:
            self.statuses = {s.mod.key: s for s in statuses}
        for key, mod in COMPAT_MODS.items():
            self.statuses.setdefault(key, PatchStatus(mod, MISSING))
        self.refresh_tab_title()

    def refresh_tab_title(self):
        on = sum(1 for v in self.enabled.values() if v.get())
        warn = any(s.state not in (OK, MISSING) for s in self.statuses.values())
        self.notebook.tab(self.tab, text=T_TAB + (f" ({on})" if on else "") + (" ⚠" if warn else ""))
