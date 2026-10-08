"""Tkinter GUI for installing the Thai translation."""
from __future__ import annotations

import ctypes
import logging
import os
import queue
import sys
import threading
import traceback
from dataclasses import replace
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from core import APP_TITLE, __version__
from core.assets import help_image
from core.custom import (COMMUNITY_ID, NAME_DOUBLE, NAME_TABS, NAME_THAI, apply_name_settings, cached_stats,
                         is_name_tab, name_modes, name_settings)
from core.game_detect import find_games, game_root, identify
from core.logo import logo_image
from core.installer import EXPORT_README, check_coverage, export, install, status, uninstall
from core.options import FONTS, MODE_DOUBLE, MODE_THAI, SLOT_EN, SLOT_TR, load_options, save_options
from core.osutil import MACOS, WINDOWS, open_folder
from core.paths import app_data_dir
from gui.custom_dialog import MODE_CHOICES, MODE_LABELS
from gui.notice_dialog import show_notice
from gui.theme import BIG_BUTTON, DARK_THEME, NATIVE_CONTROLS, P, dpi_scale, init as init_theme, on_palette_change, ui
from gui.widgets import ACCENT_ICON_COLOR, Tooltip, icon, ttk_image

log = logging.getLogger(__name__)

UI_FONT = ui(10)
UI_BOLD = ui(10, "bold")
UI_TITLE = ui(15, "bold")
PREVIEW_SIZE = (620, 150)
PREVIEW_BG = "#16181c"
LOGO_PREVIEW_HEIGHT = 110
ICON_SIZE = 20
T_UPGRADE_NOTICE = ("\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e15\u0e31\u0e27\u0e40\u0e01\u0e21\u0e17\u0e35\u0e48\u0e2d\u0e31\u0e1b\u0e40\u0e27\u0e2d\u0e23\u0e4c\u0e0a\u0e31\u0e19\u0e08\u0e32\u0e01 Classic / Next-gen "
                    "\u0e43\u0e2b\u0e49\u0e25\u0e1a mod \u0e41\u0e1b\u0e25\u0e40\u0e01\u0e48\u0e32 \u0e41\u0e25\u0e30 \u0e0b\u0e48\u0e2d\u0e21\u0e44\u0e1f\u0e25\u0e4c\u0e40\u0e01\u0e21 "
                    "\u0e01\u0e48\u0e2d\u0e19\u0e25\u0e07 mod \u0e15\u0e31\u0e27\u0e19\u0e35\u0e49 "
                    "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2b\u0e25\u0e35\u0e01\u0e40\u0e25\u0e35\u0e48\u0e22\u0e07 font \u0e44\u0e17\u0e22\u0e44\u0e21\u0e48\u0e17\u0e33\u0e07\u0e32\u0e19 "
                    "\u0e2b\u0e23\u0e37\u0e2d\u0e40\u0e1e\u0e35\u0e49\u0e22\u0e19")
T_ONEDRIVE_WARNING = ("\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e23\u0e17\u0e23\u0e32\u0e1a : \u0e42\u0e1b\u0e23\u0e14\u0e40\u0e0a\u0e47\u0e04\u0e41\u0e25\u0e30\u0e1b\u0e34\u0e14 OneDrive "
                      "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2b\u0e25\u0e35\u0e01\u0e40\u0e25\u0e35\u0e48\u0e22\u0e07\u0e1b\u0e31\u0e0d\u0e2b\u0e32\u0e40\u0e0b\u0e1f\u0e2b\u0e32\u0e22/\u0e40\u0e0b\u0e1f\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49 "
                      "\u0e41\u0e25\u0e30 error \u0e2d\u0e37\u0e48\u0e19 \u0e46 \u0e17\u0e35\u0e48\u0e40\u0e01\u0e35\u0e48\u0e22\u0e27\u0e02\u0e49\u0e2d\u0e07\u0e01\u0e31\u0e1a Documents")
T_DONE = "\u0e15\u0e34\u0e14\u0e15\u0e31\u0e49\u0e07\u0e40\u0e2a\u0e23\u0e47\u0e08\u0e41\u0e25\u0e49\u0e27"
T_DONE_NOTICE = (f"{T_DONE} \u0e16\u0e49\u0e32\u0e20\u0e32\u0e29\u0e32\u0e43\u0e19\u0e40\u0e01\u0e21\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e40\u0e1b\u0e25\u0e35\u0e48\u0e22\u0e19 "
                 "\u0e43\u0e2b\u0e49\u0e40\u0e02\u0e49\u0e32 \u0e15\u0e31\u0e49\u0e07\u0e04\u0e48\u0e32 > \u0e20\u0e32\u0e29\u0e32 > \u0e44\u0e17\u0e22")
T_REPORT_BUTTON = "\u0e2a\u0e48\u0e07\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19\u0e1b\u0e31\u0e0d\u0e2b\u0e32..."
T_EXPORT_BUTTON = "สร้างไฟล์ไว้ copy เอง..."
T_EXPORTED = "สร้างไฟล์เสร็จแล้ว"
T_FIX_PERMISSION = ("\u0e43\u0e2b\u0e49\u0e41\u0e01\u0e49\u0e2a\u0e34\u0e17\u0e18\u0e34\u0e4c\u0e02\u0e2d\u0e07\u0e42\u0e1f\u0e25\u0e40\u0e14\u0e2d\u0e23\u0e4c\u0e40\u0e01\u0e21 "
                    "(\u0e04\u0e25\u0e34\u0e01\u0e02\u0e27\u0e32 > Get Info > Sharing & Permissions) "
                    "\u0e41\u0e25\u0e49\u0e27\u0e25\u0e2d\u0e07\u0e43\u0e2b\u0e21\u0e48")
T_SLOT_EN_HINT = "\u0e43\u0e19\u0e40\u0e01\u0e21\u0e43\u0e2b\u0e49\u0e15\u0e31\u0e49\u0e07\u0e20\u0e32\u0e29\u0e32\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e40\u0e1b\u0e47\u0e19 English"
T_TAB_STYLE = "สี ขนาด ตำแหน่ง"
T_TAB_NAMES = "ชื่อเฉพาะ"
T_NAMES_HINT = ("แปลชื่อตัวละคร เมือง เควส มอนสเตอร์ และอื่นๆ เป็นภาษาไทย "
                "หมวดที่ไม่เลือก และชื่อที่ยังไม่มีคำแปล จะแสดงเป็นภาษาอังกฤษตามเกม")
T_NAMES_MIXED = "ตอนนี้ตั้งแยกรายหมวดอยู่ เลือกด้านบนเพื่อใช้แบบเดียวกันทุกหมวด"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  v{__version__}")
        self.minsize(700, 640)
        init_theme(self)
        style = ttk.Style(self)
        if not DARK_THEME and "vista" in style.theme_names():
            style.theme_use("vista")
        if not NATIVE_CONTROLS:  # aqua already uses the system font and its own control metrics
            self.option_add("*TCombobox*Listbox.font", UI_FONT)
            style.configure(".", font=UI_FONT)
            style.configure(BIG_BUTTON, font=UI_BOLD, padding=(18, 7))
            style.configure("Icon.TButton", padding=(7, 7))
            style.configure("Danger.TButton", padding=(12, 7))
            style.configure("Split.TButton", padding=(3, 7))
            style.configure("TNotebook.Tab", padding=(16, 6))
            style.configure("Switch.TCheckbutton", font=UI_FONT)
        style.configure("Title.TLabel", font=UI_TITLE)
        style.configure("Sub.TLabel", foreground=P.hint)
        style.configure("Section.TLabel", font=UI_BOLD, foreground=P.accent)
        style.configure("Bold.TLabel", font=UI_BOLD)
        style.configure("Ok.TLabel", foreground=P.ok)
        style.configure("Bad.TLabel", foreground=P.bad)
        style.configure("Warn.TLabel", foreground=P.warn)
        if not DARK_THEME:  # the dark theme draws Danger.TButton red itself, see gui/theme.py
            style.configure("Danger.TButton", foreground=P.bad)
            # aqua's own disabled grey, matching the other buttons and following light / dark
            style.map("Danger.TButton", foreground=[
                ("disabled", "systemDisabledControlTextColor" if NATIVE_CONTROLS else P.hint)])

        self.opts = load_options()
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.preview_image = None
        self._preview_job = None
        # (game path, percent) from the last "check %"
        self.latest: tuple[str, float] | None = None

        self.v_game = tk.StringVar(value=self.opts.game_path)
        self.v_font = tk.StringVar(value=FONTS.get(self.opts.font, "CS PraKas"))
        self.v_mode = tk.StringVar(value=self.opts.mode)
        self.v_thai_first = tk.BooleanVar(value=self.opts.thai_first)
        self.v_color1 = tk.StringVar(value=self.opts.color1)
        self.v_color2 = tk.StringVar(value=self.opts.color2)
        self.v_size1 = tk.IntVar(value=self.opts.size1)
        self.v_size2 = tk.IntVar(value=self.opts.size2)
        self.v_speaker = tk.BooleanVar(value=self.opts.speaker_colors)
        self.v_speaker_dialog = tk.BooleanVar(value=self.opts.show_speaker_dialog)
        self.v_speaker_sub = tk.BooleanVar(value=self.opts.show_speaker_sub)
        self.v_storybook = tk.BooleanVar(value=self.opts.storybook)
        self.v_logo = tk.BooleanVar(value=self.opts.thai_logo)
        self.v_style = tk.BooleanVar(value=self.opts.subtitle_style)
        self.v_slot = tk.StringVar(value=self.opts.slot)
        self.v_refresh = tk.BooleanVar(value=False)
        self.v_status = tk.StringVar(value="พร้อม")
        self.v_names = {tab: tk.BooleanVar() for tab in NAME_TABS}
        self.v_tab_modes = {tab: tk.StringVar() for tab in NAME_TABS}
        # the mode every switched-on name tab shares, empty when they differ
        self.v_name_mode = tk.StringVar()

        self._build()
        self.load_name_vars(self.opts.custom_sheets)
        for var in (self.v_font, self.v_mode, self.v_thai_first, self.v_color1, self.v_color2,
                    self.v_size1, self.v_size2, self.v_speaker, self.v_speaker_dialog, self.v_speaker_sub, self.v_style,
                    *self.v_names.values(), *self.v_tab_modes.values()):
            var.trace_add("write", lambda *_: self.schedule_preview())
        for var in (*self.v_names.values(), *self.v_tab_modes.values()):
            var.trace_add("write", lambda *_: self.update_names_state())
        self.v_game.trace_add("write", lambda *_: self.refresh_game())
        self.after(50, self.detect_games)
        self.after(100, self.poll_events)
        self.after(1500, lambda: self.check_update(manual=False))
        if not self.opts.hide_upgrade_notice_v2:
            self.after(300, self.show_upgrade_notice)

    # ---------- layout ----------
    def _build(self):
        root = ttk.Frame(self, padding=(16, 12))
        root.pack(fill="both", expand=True)
        self.root_frame = root
        self.banner = None
        root.columnconfigure(0, weight=1)

        ttk.Label(root, text="ติดตั้งภาษาไทย The Witcher 3: Wild Hunt - Remastered", style="Title.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(root, text="ติดตั้งลงโฟลเดอร์ mods เท่านั้น ไม่แก้ไขไฟล์ของตัวเกม ถอนการติดตั้งได้ทุกเมื่อ",
                  style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 10))

        game = ttk.LabelFrame(root, text="โฟลเดอร์เกม", padding=10)
        game.grid(row=2, column=0, sticky="ew")
        game.columnconfigure(0, weight=1)
        self.cb_game = ttk.Combobox(game, textvariable=self.v_game)
        self.cb_game.grid(row=0, column=0, sticky="ew")
        ttk.Button(game, text="เลือก...", command=self.browse).grid(row=0, column=1, padx=(6, 0))
        self.btn_check = ttk.Button(game, text="เช็ค %", command=self.do_check)
        self.btn_check.grid(row=0, column=2, padx=(6, 0))
        self.lbl_edition = ttk.Label(game, text="")
        self.lbl_edition.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.lbl_installed = ttk.Label(game, text="")
        self.lbl_installed.grid(row=2, column=0, columnspan=3, sticky="w")
        self.lbl_latest = ttk.Label(game, text="")
        self.lbl_latest.grid(row=3, column=0, columnspan=3, sticky="w")
        self.lbl_notes = ttk.Label(game, text="", style="Warn.TLabel")
        self.lbl_notes.grid(row=4, column=0, columnspan=3, sticky="w")

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=3, column=0, sticky="nsew", pady=8)
        # Tk 8.6 on macOS (the one the release build bundles) leaves part of a tab undrawn the first
        # time it is shown, e.g. the left column of the names tab, until something forces a redraw
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.update_idletasks(), add="+")
        root.rowconfigure(3, weight=1)

        subs = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(subs, text="ซับและฟอนต์")
        subs.columnconfigure(0, weight=1, uniform="subs")
        subs.columnconfigure(1, weight=1, uniform="subs")
        left = ttk.Frame(subs)
        left.grid(row=0, column=0, sticky="nw")
        ttk.Label(left, text="ฟอนต์").grid(row=0, column=0, sticky="w")
        ttk.Combobox(left, textvariable=self.v_font, values=list(FONTS.values()), state="readonly", width=18).grid(
            row=0, column=1, sticky="w", pady=2, padx=(8, 0))
        ttk.Label(left, text="รูปแบบซับ", style="Section.TLabel").grid(row=1, column=0, columnspan=2, sticky="w",
                                                                   pady=(10, 0))
        ttk.Radiobutton(left, text="ภาษาไทยอย่างเดียว", variable=self.v_mode, value=MODE_THAI).grid(
            row=2, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(left, text="ซับสองภาษา (ไทย + อังกฤษ)", variable=self.v_mode, value=MODE_DOUBLE).grid(
            row=3, column=0, columnspan=2, sticky="w")
        self.chk_first = ttk.Checkbutton(left, text="ให้ภาษาไทยอยู่บรรทัดแรก", variable=self.v_thai_first)
        self.chk_first.grid(row=4, column=0, columnspan=2, sticky="w", padx=(20, 0))
        ttk.Label(left, text="อื่นๆ", style="Section.TLabel").grid(row=5, column=0, columnspan=2, sticky="w",
                                                               pady=(10, 0))
        ttk.Checkbutton(left, text="ซับคัตซีน Storybook ภาษาไทย", variable=self.v_storybook,
                        style="Switch.TCheckbutton").grid(
            row=6, column=0, columnspan=2, sticky="w")
        self.speaker_widgets = []
        for row, (text, var) in enumerate((("ชื่อผู้พูดในคัตซีน/บทสนทนา", self.v_speaker_dialog),
                                           ("ชื่อผู้พูดระหว่างเล่น", self.v_speaker_sub)), start=7):
            chk = ttk.Checkbutton(left, text=text, variable=var, command=self.update_states,
                                  style="Switch.TCheckbutton")
            chk.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
            self.speaker_widgets.append(chk)

        logo = ttk.Frame(subs)
        logo.grid(row=0, column=1, sticky="nw")
        ttk.Checkbutton(logo, text="โลโก้ภาษาไทยในเมนูหลัก", variable=self.v_logo,
                        style="Switch.TCheckbutton").pack(anchor="w")
        self.logo_preview = tk.Label(logo, bg=PREVIEW_BG, cursor="hand2", borderwidth=0)
        self.logo_preview.pack(anchor="w", pady=(6, 0))
        self.logo_preview.bind("<Button-1>", lambda _e: self.v_logo.set(not self.v_logo.get()))
        self.logo_images = self._logo_images()
        self.v_logo.trace_add("write", lambda *_: self.update_logo_preview())
        self.update_logo_preview()

        self._build_names_tab()

        right = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(right, text=T_TAB_STYLE)
        right.columnconfigure(1, weight=1)
        ttk.Checkbutton(right, text="\u0e1b\u0e23\u0e31\u0e1a\u0e2a\u0e35 \u0e02\u0e19\u0e32\u0e14 \u0e41\u0e25\u0e30\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07\u0e0b\u0e31\u0e1a (\u0e41\u0e01\u0e49 script \u0e43\u0e19 mods)", variable=self.v_style,
                        command=self.update_states, style="Switch.TCheckbutton").grid(row=0, column=0, columnspan=3, sticky="w")
        # the speaker name switches on the first tab also need the script mod
        self.style_widgets = list(self.speaker_widgets)
        for row, (label, cvar, svar) in enumerate((("บรรทัดที่ 1", self.v_color1, self.v_size1),
                                                    ("บรรทัดที่ 2", self.v_color2, self.v_size2)), start=1):
            ttk.Label(right, text=label).grid(row=row * 2 - 1, column=0, sticky="w", pady=(8, 0))
            swatch = tk.Label(right, width=4, relief="flat", bg=cvar.get(), cursor="hand2",
                              highlightthickness=1, highlightbackground="#5a5a5a")
            swatch.grid(row=row * 2 - 1, column=1, sticky="w", pady=(8, 0), padx=6)
            swatch.bind("<Button-1>", lambda _e, v=cvar: self.pick_color(v))
            cvar.trace_add("write", lambda *_, v=cvar, s=swatch: s.configure(bg=v.get()))
            btn = ttk.Button(right, text="เลือกสี", command=lambda v=cvar: self.pick_color(v))
            btn.grid(row=row * 2 - 1, column=2, sticky="e", pady=(8, 0))
            scale = ttk.Scale(right, from_=16, to=48, orient="horizontal",
                              command=lambda val, v=svar: v.get() != int(float(val)) and v.set(int(float(val))))
            scale.set(svar.get())
            svar.trace_add("write", lambda *_, v=svar, s=scale: s.set(v.get()))
            scale.grid(row=row * 2, column=0, columnspan=2, sticky="ew")
            size_lbl = ttk.Label(right, textvariable=svar, width=3)
            size_lbl.grid(row=row * 2, column=2, sticky="e")
            self.style_widgets += [swatch, btn, scale]
        self.chk_speaker = ttk.Checkbutton(right, text="ชื่อผู้พูดเป็นสี", variable=self.v_speaker,
                                           style="Switch.TCheckbutton")
        self.chk_speaker.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.style_widgets.append(self.chk_speaker)
        layout = ttk.Frame(right)
        layout.grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.btn_layout = ttk.Button(layout, text="\u0e1b\u0e23\u0e31\u0e1a\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07...",
                                     command=self.open_layout, width=16)
        self.btn_layout.pack(side="left")
        self.lbl_layout = ttk.Label(layout, text="")
        self.lbl_layout.pack(side="left", padx=(6, 0))
        self.style_widgets.append(self.btn_layout)
        self.update_layout_label()
        ttk.Button(right, text="คืนค่าเริ่มต้น", command=self.reset_style).grid(row=7, column=0, columnspan=3,
                                                                           sticky="w", pady=(8, 0))
        self.v_mode.trace_add("write", lambda *_: self.update_states())

        adv = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(adv, text="ขั้นสูง")
        ttk.Label(adv, text="ช่องภาษาในเกม", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(adv, text="แทน Turkish (เมนูแสดงเป็น \"ไทย\") - แนะนำ", variable=self.v_slot,
                        value=SLOT_TR).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(adv, text="แทนภาษาอังกฤษ (สำหรับเกมจาก Xbox)", variable=self.v_slot, value=SLOT_EN).grid(
            row=2, column=0, sticky="w")
        ttk.Label(adv, text="คำแปล", style="Section.TLabel").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Checkbutton(adv, text="ดาวน์โหลดคำแปลล่าสุดทุกครั้ง", variable=self.v_refresh,
                        style="Switch.TCheckbutton").grid(
            row=4, column=0, sticky="w")
        custom = ttk.Frame(adv)
        custom.grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Button(custom, text="คำแปลเสริมอื่นๆ...", command=self.open_custom).pack(side="left")
        self.lbl_custom = ttk.Label(custom, text="")
        self.lbl_custom.pack(side="left", padx=(6, 0))
        self.update_custom_label()

        prev = ttk.LabelFrame(root, text="ตัวอย่างซับในเกม", padding=6)
        prev.grid(row=4, column=0, sticky="ew")
        self.preview = tk.Canvas(prev, bg=PREVIEW_BG, width=PREVIEW_SIZE[0], height=PREVIEW_SIZE[1],
                                 highlightthickness=0)
        self.preview.pack(fill="x")
        self.preview.bind("<Configure>", lambda _e: self.schedule_preview())

        bottom = ttk.Frame(root)
        bottom.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(bottom, maximum=1000)
        self.progress.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(bottom, textvariable=self.v_status).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 6))

        left = ttk.Frame(bottom)
        left.grid(row=2, column=0, sticky="w")
        for name, label, command in (("update", "ตรวจสอบอัปเดต", lambda: self.check_update(manual=True)),
                                     ("bug_report", T_REPORT_BUTTON, self.open_report),
                                     ("folder_open", "เปิดโฟลเดอร์ mods", self.open_mods)):
            image = ttk_image(self, name, ICON_SIZE)
            btn = ttk.Button(left, image=image, text="" if image else label, style="Icon.TButton", command=command)
            btn.pack(side="left", padx=(0, 4))
            Tooltip(btn, label.rstrip("."))

        right = ttk.Frame(bottom)
        right.grid(row=2, column=1, sticky="e")
        self.btn_install = ttk.Button(right, text="ติดตั้ง / อัปเดต", image=ttk_image(self, "download", ICON_SIZE, ACCENT_ICON_COLOR),
                                      compound="left", style=BIG_BUTTON, command=self.do_install)
        self.btn_install.pack(side="left")
        self.menu_install = self._make_menu((("drive_file_move", T_EXPORT_BUTTON, self.do_export),))
        self.btn_install_more = ttk.Button(right, image=ttk_image(self, "expand_more", ICON_SIZE), style="Split.TButton",
                                           command=lambda: self.popup_menu(self.menu_install, self.btn_install))
        self.btn_install_more.pack(side="left", fill="y")
        Tooltip(self.btn_install_more, T_EXPORT_BUTTON.rstrip("."))
        self.btn_uninstall = ttk.Button(right, text="ถอนการติดตั้ง",
                                        image=ttk_image(self, "delete", ICON_SIZE, "#ffffff" if DARK_THEME else P.bad),
                                        compound="left",
                                        style="Danger.TButton", command=self.do_uninstall)
        self.btn_uninstall.pack(side="left", padx=(6, 0), fill="y")
        if not DARK_THEME:  # the icon is drawn in the palette's red, which differs between light and dark
            on_palette_change.append(lambda: self.btn_uninstall.configure(
                image=ttk_image(self, "delete", ICON_SIZE, P.bad)))
        self.update_states()

    def _logo_images(self) -> dict[bool, ImageTk.PhotoImage] | None:
        """The Thai logo on the preview background, bright when switched on and dimmed when off."""
        try:
            logo = Image.open(logo_image()).convert("RGBA")
        except OSError as exc:
            log.warning("logo preview: %s", exc)
            return None
        logo = logo.crop(logo.getbbox())
        height = round(LOGO_PREVIEW_HEIGHT * dpi_scale(self))
        logo = logo.resize((max(1, logo.width * height // logo.height), height), Image.LANCZOS)
        pad = height // 10
        images = {}
        for on in (True, False):
            img = logo if on else logo.copy()
            if not on:
                img.putalpha(img.getchannel("A").point(lambda a: a * 30 // 100))
            bg = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), PREVIEW_BG)
            bg.alpha_composite(img, (pad, pad))
            images[on] = ImageTk.PhotoImage(bg.convert("RGB"), master=self)
        return images

    def update_logo_preview(self):
        if self.logo_images:
            self.logo_preview.configure(image=self.logo_images[bool(self.v_logo.get())])
        else:
            self.logo_preview.pack_forget()

    def _build_names_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.names_tab = tab
        self.notebook.add(tab, text=T_TAB_NAMES)
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        hint = ttk.Label(tab, text=T_NAMES_HINT, wraplength=640, justify="left")
        hint.grid(row=0, column=0, columnspan=2, sticky="ew")
        tab.bind("<Configure>", lambda e: hint.configure(wraplength=max(200, e.width - 24)))

        grid = ttk.Frame(tab)
        grid.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        grid.columnconfigure(2, weight=1, minsize=24)
        grid.columnconfigure(5, weight=1)
        self.name_checks = {}
        self.name_combos = {}
        for i, name in enumerate(NAME_TABS):
            r, c = i // 2, (i % 2) * 3
            chk = ttk.Checkbutton(grid, variable=self.v_names[name])
            chk.grid(row=r, column=c, sticky="w", pady=1)
            combo = ttk.Combobox(grid, textvariable=self.v_tab_modes[name], values=list(MODE_LABELS.values()),
                                 state="readonly", width=7)
            combo.grid(row=r, column=c + 1, sticky="w", padx=(8, 0), pady=1)
            self.name_checks[name] = chk
            self.name_combos[name] = combo
        self.update_name_labels()
        buttons = ttk.Frame(tab)
        buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(buttons, text="เลือกทั้งหมด", command=lambda: self.set_all_names(True)).pack(side="left")
        ttk.Button(buttons, text="ไม่เลือกเลย", command=lambda: self.set_all_names(False)).pack(
            side="left", padx=(6, 0))

        ttk.Label(tab, text="รูปแบบชื่อทุกหมวด", style="Section.TLabel").grid(row=3, column=0, columnspan=2,
                                                                           sticky="w", pady=(10, 0))
        modes = ttk.Frame(tab)
        modes.grid(row=4, column=0, columnspan=2, sticky="w")
        self.name_mode_radios = []
        for mode in (NAME_THAI, NAME_DOUBLE):
            radio = ttk.Radiobutton(modes, text=MODE_CHOICES[mode], variable=self.v_name_mode, value=mode,
                                    command=lambda m=mode: self.set_all_name_modes(m))
            radio.pack(side="left", padx=(0, 16))
            self.name_mode_radios.append(radio)
        self.lbl_name_mixed = ttk.Label(tab, text="", foreground=P.hint)
        self.lbl_name_mixed.grid(row=5, column=0, columnspan=2, sticky="w")

    def update_name_labels(self):
        for name, chk in self.name_checks.items():
            percent = cached_stats(COMMUNITY_ID, name)[1]
            label = name.removeprefix("ชื่อ")
            chk.configure(text=f"{label} (แปลแล้ว {percent:.0%})" if percent is not None else label)

    def set_all_names(self, on: bool):
        for var in self.v_names.values():
            var.set(on)

    def set_all_name_modes(self, mode: str):
        for var in self.v_tab_modes.values():
            var.set(MODE_LABELS[mode])

    def tab_modes(self) -> dict[str, str]:
        return {tab: next(k for k, v in MODE_LABELS.items() if v == var.get())
                for tab, var in self.v_tab_modes.items()}

    def load_name_vars(self, sheets: list[dict]):
        enabled, _mode = name_settings(sheets)
        for name, var in self.v_names.items():
            var.set(name in enabled)
        for name, mode in name_modes(sheets).items():
            self.v_tab_modes[name].set(MODE_LABELS[mode])
        self.update_names_state()

    def update_names_state(self):
        on = {tab for tab, var in self.v_names.items() if var.get()}
        self.notebook.tab(self.names_tab, text=f"{T_TAB_NAMES} ({len(on)}/{len(self.v_names)})")
        for tab, combo in self.name_combos.items():
            combo.configure(state="readonly" if tab in on else "disabled")
        for radio in self.name_mode_radios:
            radio.configure(state="normal" if on else "disabled")
        shared = {mode for tab, mode in self.tab_modes().items() if tab in on}
        mode = shared.pop() if len(shared) == 1 else ""
        if self.v_name_mode.get() != mode:
            self.v_name_mode.set(mode)
        self.lbl_name_mixed.configure(text=T_NAMES_MIXED if len(on) and not mode else "")

    def _make_menu(self, items) -> tk.Menu:
        menu = tk.Menu(self, tearoff=False) if NATIVE_CONTROLS else tk.Menu(self, tearoff=False, font=UI_FONT)
        for name, label, command in items:
            image = icon(self, name, ICON_SIZE)
            menu.add_command(label=f"  {label}", command=command, **({"image": image, "compound": "left"}
                                                                      if image else {}))
        return menu

    def popup_menu(self, menu: tk.Menu, anchor, align_right: bool = False):
        menu.update_idletasks()
        x = anchor.winfo_rootx()
        if align_right:
            x += anchor.winfo_width() - menu.winfo_reqwidth()
        try:
            menu.tk_popup(x, anchor.winfo_rooty() + anchor.winfo_height())
        finally:
            menu.grab_release()

    # ---------- helpers ----------
    def current_options(self):
        font_key = next((k for k, v in FONTS.items() if v == self.v_font.get()), "CSPraKas")
        return replace(self.opts, game_path=self.v_game.get().strip(), font=font_key, mode=self.v_mode.get(),
                       thai_first=self.v_thai_first.get(), color1=self.v_color1.get(), color2=self.v_color2.get(),
                       size1=int(self.v_size1.get()), size2=int(self.v_size2.get()),
                       speaker_colors=self.v_speaker.get(), show_speaker_dialog=self.v_speaker_dialog.get(),
                       show_speaker_sub=self.v_speaker_sub.get(), storybook=self.v_storybook.get(),
                       thai_logo=self.v_logo.get(), subtitle_style=self.v_style.get(), slot=self.v_slot.get(),
                       custom_sheets=apply_name_settings(
                           self.opts.custom_sheets, {t for t, v in self.v_names.items() if v.get()},
                           self.tab_modes()))

    def update_custom_label(self):
        sheets = [s for s in self.opts.custom_sheets if not is_name_tab(s)]
        on = sum(1 for s in sheets if s.get("enabled"))
        self.lbl_custom.configure(text=f"เปิดใช้ {on} จาก {len(sheets)} ไฟล์ (ไม่นับแท็บ{T_TAB_NAMES})")

    def open_report(self):
        from gui.report_dialog import ReportDialog

        ReportDialog(self, self.v_game.get().strip())

    def open_custom(self):
        from gui.custom_dialog import CustomSheetsDialog

        def on_save(sheets):
            self.opts = replace(self.current_options(), custom_sheets=sheets)
            save_options(self.opts)
            self.load_name_vars(sheets)
            self.update_name_labels()
            self.update_custom_label()
        CustomSheetsDialog(self, self.current_options().custom_sheets, on_save)

    def update_layout_label(self):
        o = self.opts
        if (o.sub_x, o.sub_y, o.sub_width, o.dialog_x, o.dialog_y, o.choice_x, o.choice_y, o.choice_scale) == (0, 0, 100, 0, 0, 0, 0, 100):
            text = "\u0e04\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
        else:
            text = "\u0e1b\u0e23\u0e31\u0e1a\u0e41\u0e25\u0e49\u0e27"
        self.lbl_layout.configure(text=text)

    def open_layout(self):
        from gui.hud_layout_dialog import HudLayoutDialog

        def on_save(values):
            if "size1" in values:
                self.v_size1.set(values["size1"])
                self.v_size2.set(values["size2"])
            self.opts = replace(self.current_options(), **values)
            save_options(self.opts)
            self.update_layout_label()
        HudLayoutDialog(self, self.current_options(), on_save)

    def update_states(self):
        state = "normal" if self.v_style.get() else "disabled"
        for w in self.style_widgets:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass
        if not (self.v_speaker_dialog.get() or self.v_speaker_sub.get()):
            self.chk_speaker.configure(state="disabled")
        self.chk_first.configure(state="normal" if self.v_mode.get() == MODE_DOUBLE else "disabled")
        self.schedule_preview()

    def pick_color(self, var: tk.StringVar):
        if not self.v_style.get():
            return
        _rgb, hex_color = colorchooser.askcolor(color=var.get(), parent=self)
        if hex_color:
            var.set(hex_color.upper())

    def reset_style(self):
        self.v_color1.set("#FFFFFF")
        self.v_color2.set("#808080")
        self.v_size1.set(28)
        self.v_size2.set(28)
        self.v_speaker.set(True)
        self.opts = replace(self.opts, sub_x=0.0, sub_y=0.0, sub_width=100, dialog_x=0.0, dialog_y=0.0,
                            choice_x=0.0, choice_y=0.0, choice_scale=100)
        self.update_layout_label()

    def schedule_preview(self):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(120, self.render_preview)

    def render_preview(self):
        self._preview_job = None
        try:
            from PIL import ImageTk
            from gui.preview import render
            width = max(200, self.preview.winfo_width())
            img = render(self.current_options(), width, PREVIEW_SIZE[1])
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview.delete("all")
            self.preview.create_image(0, 0, image=self.preview_image, anchor="nw")
        except Exception:
            log.exception("preview failed")

    # ---------- self update ----------
    def check_update(self, manual: bool):
        from core.update import check_for_update

        if manual:
            self.v_status.set("กำลังตรวจสอบเวอร์ชันใหม่...")

        def work():
            try:
                self.events.put(("update", check_for_update(), manual))
            except Exception as exc:
                log.info("update check failed: %s", exc)
                self.events.put(("update_error", str(exc), manual))
        threading.Thread(target=work, daemon=True).start()

    def on_update(self, info, manual: bool):
        from gui.update_dialog import UpdateBanner, UpdateDialog

        if info is None:
            if manual:
                self.v_status.set(f"ใช้เวอร์ชันล่าสุดอยู่แล้ว (v{__version__})")
            return
        if self.banner is None or not self.banner.winfo_exists():
            self.banner = UpdateBanner(self, info)
            self.banner.pack(fill="x", before=self.root_frame)
        if manual:
            self.v_status.set(f"มีเวอร์ชันใหม่ v{info.version}")
            UpdateDialog(self, info)

    # ---------- game detection ----------
    def detect_games(self):
        def work():
            try:
                games = find_games()
            except Exception:
                log.exception("detect failed")
                games = []
            self.events.put(("games", games))
        threading.Thread(target=work, daemon=True).start()

    def browse(self):
        path = filedialog.askdirectory(parent=self, title="เลือกโฟลเดอร์เกม The Witcher 3",
                                       initialdir=self.v_game.get() or None)
        if path:
            self.v_game.set(os.path.normpath(game_root(path)))

    def refresh_game(self):
        path = self.v_game.get().strip()
        if not path:
            self.lbl_edition.configure(text="ยังไม่ได้เลือกโฟลเดอร์เกม", style="Bad.TLabel")
            self.lbl_installed.configure(text="")
            self.lbl_latest.configure(text="")
            self.lbl_notes.configure(text="")
            self.btn_install.configure(state="disabled")
            self.btn_check.configure(state="disabled")
            self._set_more_states(False, False)
            self._fit_status_labels()
            return
        game = identify(path)
        ok = game.supported
        label = game.label + (f" (v{game.version})" if game.version else "")
        self.lbl_edition.configure(text=("✔ " if ok else "✖ ") + label, style="Ok.TLabel" if ok else "Bad.TLabel")
        self.lbl_notes.configure(text="\n".join("⚠ " + n for n in game.notes))
        self.btn_install.configure(state="normal" if ok and not self.busy else "disabled")
        self.btn_check.configure(state="normal" if ok and not self.busy else "disabled")
        st = status(game) if ok else None
        if st and st.installed:
            text = f"ติดตั้งแล้ว v{st.version or '?'}"
            if st.installed_at:
                text += f" เมื่อ {st.installed_at}"
            if st.percent:
                text += f" (แปลแล้ว {st.percent:.1f}%)"
        else:
            text = "ยังไม่ได้ติดตั้งภาษาไทย" if ok else ""
        if st and st.legacy_mods:
            text += "  |  พบ mod ไทยตัวเก่า: " + ", ".join(st.legacy_mods)
        if st and st.foreign_mods:
            text += "  |  พบ mod ไทยจากที่อื่น (กดติดตั้งเพื่อย้ายออก): " + ", ".join(st.foreign_mods)
        if st and st.modified:
            text += "  |  ไฟล์ mod ถูกเปลี่ยนหลังติดตั้ง กดติดตั้งใหม่"
        self.lbl_installed.configure(text=text)
        self.lbl_latest.configure(**self._latest_text(path, st if ok else None))
        self._fit_status_labels()
        self._set_more_states(ok, bool(st and st.installed))

    def _fit_status_labels(self):
        """Empty status lines take no room."""
        for lbl in (self.lbl_installed, self.lbl_latest, self.lbl_notes):
            if lbl.cget("text"):
                lbl.grid()
            else:
                lbl.grid_remove()

    def _set_more_states(self, export_ok: bool, uninstall_ok: bool):
        self.btn_install_more.configure(state="normal" if export_ok and not self.busy else "disabled")
        self.btn_uninstall.configure(state="normal" if uninstall_ok and not self.busy else "disabled")

    def _latest_text(self, path: str, st) -> dict:
        if not self.latest or self.latest[0] != path or st is None:
            return {"text": "", "style": "TLabel"}
        latest = round(self.latest[1], 1)
        if not st.installed:
            return {"text": f"ถ้าติดตั้งตอนนี้: แปลได้ {latest:.1f}%", "style": "TLabel"}
        diff = latest - round(st.percent, 1)
        if diff > 0:
            return {"text": f"ถ้าติดตั้งใหม่ตอนนี้: แปลได้ {latest:.1f}% (+{diff:.1f}%) กดติดตั้งเพื่ออัปเดต",
                    "style": "Ok.TLabel"}
        if diff < 0:
            return {"text": f"ถ้าติดตั้งใหม่ตอนนี้: แปลได้ {latest:.1f}% ({diff:.1f}% นับชื่อเฉพาะที่ยังไม่มีชื่อไทยด้วย)",
                    "style": "TLabel"}
        return {"text": f"ถ้าติดตั้งใหม่ตอนนี้: แปลได้ {latest:.1f}% (ติดตั้งไว้เป็นล่าสุดแล้ว)", "style": "TLabel"}

    # ---------- actions ----------
    def do_check(self):
        opts = self.current_options()
        self.set_busy(True)
        self.progress["value"] = 0

        def progress(fraction, message):
            self.events.put(("progress", fraction, message))

        def work():
            try:
                self.events.put(("checked", opts.game_path, check_coverage(opts, progress)))
            except Exception as exc:
                log.error("check failed\n%s", traceback.format_exc())
                self.events.put(("check_error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def set_busy(self, busy: bool):
        self.busy = busy
        self.cb_game.configure(state="disabled" if busy else "normal")
        self.configure(cursor="watch" if busy else "")
        self.refresh_game()

    def do_install(self):
        opts = self.current_options()
        try:
            opts.validate()
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self)
            return
        self.opts = opts
        save_options(opts)
        self.set_busy(True)
        self.progress["value"] = 0
        refresh = self.v_refresh.get()

        def progress(fraction, message):
            self.events.put(("progress", fraction, message))

        def confirm(message):
            answer = {}
            done = threading.Event()
            self.events.put(("confirm", message, answer, done))
            done.wait()
            return answer.get("yes", False)

        def work():
            try:
                report = install(opts, progress, confirm, force_download=refresh)
                self.events.put(("installed", report))
            except PermissionError as exc:
                log.warning("install permission denied: %s", exc)
                self.events.put(("permission", str(exc)))
            except Exception as exc:
                log.error("install failed\n%s", traceback.format_exc())
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def do_export(self):
        opts = self.current_options()
        try:
            opts.validate()
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self)
            return
        out_dir = filedialog.askdirectory(parent=self, title="เลือกที่เก็บไฟล์ภาษาไทย (จะสร้างโฟลเดอร์ ThaiW3_mods ในนี้)",
                                          initialdir=str(Path.home() / "Desktop"))
        if not out_dir:
            return
        self.opts = opts
        save_options(opts)
        self.set_busy(True)
        self.progress["value"] = 0
        refresh = self.v_refresh.get()

        def progress(fraction, message):
            self.events.put(("progress", fraction, message))

        def work():
            try:
                self.events.put(("exported", export(opts, out_dir, progress, force_download=refresh)))
            except Exception as exc:
                log.error("export failed\n%s", traceback.format_exc())
                self.events.put(("export_error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def do_uninstall(self):
        path = self.v_game.get().strip()
        if not messagebox.askyesno(APP_TITLE, "ต้องการถอน mod ภาษาไทยออกจากเกมหรือไม่?", parent=self):
            return
        try:
            removed = uninstall(path)
        except PermissionError as exc:
            log.warning("uninstall permission denied: %s", exc)
            self.ask_elevate("ไม่มีสิทธิ์ลบไฟล์ในโฟลเดอร์ mods")
            return
        except OSError as exc:
            log.warning("uninstall failed: %s", exc)
            messagebox.showerror(APP_TITLE, f"ถอนการติดตั้งไม่สำเร็จ: {exc}\nลองปิดเกมก่อนแล้วลองใหม่", parent=self)
            return
        self.v_status.set("ถอนการติดตั้งแล้ว: " + (", ".join(removed) or "-"))
        self.progress["value"] = 0
        self.refresh_game()

    def open_mods(self):
        path = game_root(self.v_game.get().strip()) / "mods"
        target = path if path.is_dir() else path.parent
        if target.is_dir():
            open_folder(target)

    def ask_elevate(self, message: str):
        if not WINDOWS:  # no UAC to ask; on macOS the game folder's own permissions are the fix
            messagebox.showerror(APP_TITLE, f"{message}\n{T_FIX_PERMISSION}", parent=self)
            return
        if messagebox.askyesno(APP_TITLE, f"{message}\nต้องการเปิดโปรแกรมใหม่ด้วยสิทธิ์ผู้ดูแลระบบ (Administrator) หรือไม่?",
                               parent=self):
            params = " ".join(f'"{a}"' for a in sys.argv[1:]) if not getattr(sys, "frozen", False) else ""
            exe = sys.executable
            if not getattr(sys, "frozen", False):
                params = f'"{os.path.abspath(sys.argv[0])}" {params}'
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            self.destroy()

    def poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "games":
                    games = event[1]
                    self.cb_game.configure(values=[str(g.path) for g in games])
                    supported = [g for g in games if g.supported]
                    if not self.v_game.get() and supported:
                        self.v_game.set(str(supported[0].path))
                    else:
                        self.refresh_game()
                    if not games and not self.v_game.get():
                        self.v_status.set("ไม่พบเกมอัตโนมัติ กรุณากด \"เลือก...\" เพื่อระบุโฟลเดอร์เกม")
                elif kind == "update":
                    self.on_update(event[1], event[2])
                elif kind == "update_error":
                    if event[2]:
                        self.v_status.set("ตรวจสอบเวอร์ชันใหม่ไม่ได้ (ไม่มีอินเทอร์เน็ตหรือ GitHub ไม่ตอบ)")
                elif kind == "progress":
                    self.progress["value"] = int(event[1] * 1000)
                    self.v_status.set(event[2])
                elif kind == "confirm":
                    _k, message, answer, done = event
                    answer["yes"] = messagebox.askyesno(APP_TITLE, message, parent=self)
                    done.set()
                elif kind == "checked":
                    report = event[2]
                    self.latest = (event[1], report.percent)
                    self.v_status.set(f"คำแปลล่าสุด: แปลได้ {report.percent:.2f}% "
                                      f"({report.translated:,}/{report.total:,} ข้อความ)")
                    self.set_busy(False)
                elif kind == "check_error":
                    self.set_busy(False)
                    self.v_status.set(f"เช็คคำแปลล่าสุดไม่สำเร็จ: {event[1]}")
                elif kind == "installed":
                    self.latest = None
                    self.set_busy(False)
                    self.on_installed(event[1])
                elif kind == "exported":
                    self.set_busy(False)
                    self.on_exported(event[1])
                elif kind == "export_error":
                    self.set_busy(False)
                    self.v_status.set("สร้างไฟล์ไม่สำเร็จ")
                    messagebox.showerror(APP_TITLE, f"สร้างไฟล์ไม่สำเร็จ:\n{event[1]}\n\nดูรายละเอียดได้ที่ {log_path()}",
                                         parent=self)
                elif kind == "permission":
                    self.set_busy(False)
                    self.v_status.set(event[1])
                    self.ask_elevate(event[1])
                elif kind == "error":
                    self.set_busy(False)
                    self.v_status.set("ติดตั้งไม่สำเร็จ")
                    messagebox.showerror(APP_TITLE, f"ติดตั้งไม่สำเร็จ:\n{event[1]}\n\nดูรายละเอียดได้ที่ {log_path()}",
                                         parent=self)
        except queue.Empty:
            pass
        self.after(100, self.poll_events)

    def show_upgrade_notice(self):
        if show_notice(self, APP_TITLE, T_UPGRADE_NOTICE, bold=True, warning=_onedrive_warning()):
            self.opts.hide_upgrade_notice_v2 = True
            save_options(self.opts)

    def on_exported(self, report):
        self.v_status.set(f"{T_EXPORTED}  แปลแล้ว {report.percent:.2f}%  {report.output}")
        game = identify(self.opts.game_path)
        lines = [f"{T_EXPORTED} ที่ {report.output}", "",
                 f"คัดลอกโฟลเดอร์ {', '.join(report.mods)} ไปไว้ในโฟลเดอร์ mods ของเกม",
                 f"{game.mods_dir}",
                 f"(ขั้นตอนละเอียดอยู่ในไฟล์ {EXPORT_README})", "",
                 f"แปลแล้ว {report.percent:.2f}% ({report.translated:,}/{report.total:,} ข้อความ)"]
        if report.warnings:
            lines += ["", "ข้อควรทราบ:"] + [f"- {w}" for w in report.warnings]
        messagebox.showinfo(APP_TITLE, "\n".join(lines), parent=self)
        if os.path.isdir(report.output):
            open_folder(report.output)

    def on_installed(self, report):
        lines = [f"\u0e41\u0e1b\u0e25\u0e41\u0e25\u0e49\u0e27 {report.percent:.2f}% ({report.translated:,}/{report.total:,} \u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21)",
                 f"\u0e04\u0e33\u0e41\u0e1b\u0e25\u0e08\u0e32\u0e01: {report.source} ({report.fetched})"]
        if report.custom:
            lines.append(f"\u0e04\u0e33\u0e41\u0e1b\u0e25\u0e40\u0e2a\u0e23\u0e34\u0e21\u0e17\u0e35\u0e48\u0e40\u0e1b\u0e34\u0e14\u0e43\u0e0a\u0e49: {report.custom:,} \u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21")
        warnings = ["\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e23\u0e17\u0e23\u0e32\u0e1a:"] + [f"- {w}" for w in report.warnings] if report.warnings else []
        self.v_status.set(f"{T_DONE}  {lines[0]}")
        if self.opts.hide_done_notice_v2:
            if warnings:
                messagebox.showwarning(APP_TITLE, "\n".join(warnings), parent=self)
            return
        thai_slot = self.opts.slot == SLOT_TR
        head = T_DONE_NOTICE if thai_slot else f"{T_DONE}\n{T_SLOT_EN_HINT}"
        message = "\n".join([head, ""] + lines + ([""] + warnings if warnings else []))
        if show_notice(self, APP_TITLE, message, help_image("game_language_thai") if thai_slot else None,
                       warning=_onedrive_warning()):
            self.opts.hide_done_notice_v2 = True
            save_options(self.opts)


def _onedrive_warning() -> str | None:
    """Documents redirected into OneDrive only bites on Windows."""
    return T_ONEDRIVE_WARNING if WINDOWS else None


def log_path() -> Path:
    return app_data_dir() / "install.log"


def run() -> None:
    logging.basicConfig(filename=log_path(), level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if WINDOWS:  # macOS scales the whole UI itself
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    app = App()
    if MACOS:  # a plain python process opens its window behind whatever launched it
        app.lift()
        app.attributes("-topmost", True)
        app.after_idle(app.attributes, "-topmost", False)
    app.mainloop()
