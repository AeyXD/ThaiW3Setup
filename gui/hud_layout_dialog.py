"""Dialog for moving the HUD subtitles, the dialogue line and the dialogue choices on a mock 16:9 screen.

Thai UI strings are written as \\u escapes.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, replace
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from core.assets import layout_background
from core.options import LAYOUT_BGS, MODE_DOUBLE, OFFSET_LIMIT, SCALE_RANGE, WIDTH_RANGE, InstallOptions
from gui.theme import P, ui
from gui.preview import descent_px, subtitle_block, text_rows

REF_W, REF_H = 1920, 1080
CANVAS_W, CANVAS_H = 768, 432
STAGE_BG = "#0b0c0d"

# Vanilla layout at 1920x1080. The dialogue positions are the mcSubtitlesContainer and
# mcOptionContainer placements in hud_dialog.redswf. Gameplay subtitles grow upward from the
# baseline of their last line, measured from an in-game screenshot; the box width is tfSubtitles.
SUB_CENTER_X = 960
SUB_BASELINE = 838
SUB_BOX_W = 1180
LINE_CENTER_TOP = (960, 858)
# mcOptionContainer, from devtools/dump_hud_layout.py. Units after the origin are the container's
# own, multiplied by its scale on screen. The list is laid out upward from CHOICE_BOTTOM, which
# was measured from an in-game screenshot.
CHOICE_ORIGIN = (1486.2, 638.8)
CHOICE_BASE_SCALE = 1.25
CHOICE_TEXT_X = -234
CHOICE_FIELD_W = 540
CHOICE_FONT = 23
CHOICE_BOTTOM = 128
CHOICE_ARROW_W = 16
CHOICE_LINE_H = 26.7
CHOICE_GAP = 19
# (Thai, English); zero-width spaces mark Thai word breaks for wrapping.
CHOICES = [
    ("\u0e02\u0e49\u0e32\u200b\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u200b\u0e23\u0e39\u0e49\u200b"
     "\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u200b\u0e2a\u0e31\u0e0d\u0e0d\u0e32\u200b\u0e25\u0e48\u0e32\u200b"
     "\u0e2d\u0e2a\u0e39\u0e23", "Tell me about the contract."),
    ("\u0e40\u0e08\u0e49\u0e32\u200b\u0e40\u0e2b\u0e47\u0e19\u200b\u0e2b\u0e0d\u0e34\u0e07\u200b\u0e2a\u0e32\u0e27"
     "\u200b\u0e1c\u0e21\u200b\u0e2a\u0e35\u200b\u0e40\u0e17\u0e32\u200b\u0e1a\u0e49\u0e32\u0e07\u200b"
     "\u0e44\u0e2b\u0e21", "Seen a woman with ashen hair?"),
    ("\u0e44\u0e27\u0e49\u200b\u0e04\u0e38\u0e22\u200b\u0e01\u0e31\u0e19\u200b\u0e43\u0e2b\u0e21\u0e48",
     "See you."),
]
CHOICE_COLOR = "#FFFFFF"
CHOICE_ARROW = "#F8D66B"

T_TITLE = "\u0e1b\u0e23\u0e31\u0e1a\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07\u0e0b\u0e31\u0e1a\u0e43\u0e19 HUD"
T_HINT = ("\u0e25\u0e32\u0e01\u0e01\u0e25\u0e48\u0e2d\u0e07\u0e43\u0e19\u0e20\u0e32\u0e1e\u0e40\u0e1e\u0e37\u0e48\u0e2d"
          "\u0e22\u0e49\u0e32\u0e22 \u0e2b\u0e23\u0e37\u0e2d\u0e1b\u0e23\u0e31\u0e1a\u0e25\u0e30\u0e40\u0e2d\u0e35\u0e22\u0e14"
          "\u0e14\u0e49\u0e27\u0e22\u0e41\u0e16\u0e1a\u0e40\u0e25\u0e37\u0e48\u0e2d\u0e19\u0e14\u0e49\u0e32\u0e19\u0e25\u0e48"
          "\u0e32\u0e07 (\u0e2b\u0e19\u0e48\u0e27\u0e22: % \u0e02\u0e2d\u0e07\u0e08\u0e2d)")
T_SUB = "\u0e0b\u0e31\u0e1a\u0e23\u0e30\u0e2b\u0e27\u0e48\u0e32\u0e07\u0e40\u0e25\u0e48\u0e19"
T_DIALOG = "\u0e09\u0e32\u0e01\u0e2a\u0e19\u0e17\u0e19\u0e32"
T_LINE = "\u0e0b\u0e31\u0e1a\u0e09\u0e32\u0e01\u0e2a\u0e19\u0e17\u0e19\u0e32"
T_CHOICES = "\u0e01\u0e25\u0e48\u0e2d\u0e07\u0e15\u0e31\u0e27\u0e40\u0e25\u0e37\u0e2d\u0e01"
T_SUB_TAB = T_SUB + " (\u0e19\u0e2d\u0e01\u0e09\u0e32\u0e01\u0e2a\u0e19\u0e17\u0e19\u0e32)"
T_DIALOG_TAB = T_DIALOG
T_X = "\u0e0b\u0e49\u0e32\u0e22-\u0e02\u0e27\u0e32"
T_Y = "\u0e02\u0e36\u0e49\u0e19-\u0e25\u0e07"
T_WIDTH = "\u0e04\u0e27\u0e32\u0e21\u0e01\u0e27\u0e49\u0e32\u0e07 %"
T_SIZE1 = "\u0e02\u0e19\u0e32\u0e14\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14\u0e17\u0e35\u0e48 1"
T_SIZE2 = "\u0e02\u0e19\u0e32\u0e14\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14\u0e17\u0e35\u0e48 2"
T_SIZE_OFF = ("\u0e40\u0e1b\u0e34\u0e14 \u0e2a\u0e35 \u0e02\u0e19\u0e32\u0e14 \u0e41\u0e25\u0e30\u0e15\u0e33\u0e41"
              "\u0e2b\u0e19\u0e48\u0e07\u0e0b\u0e31\u0e1a \u0e43\u0e19\u0e2b\u0e19\u0e49\u0e32\u0e2b\u0e25\u0e31\u0e01"
              "\u0e01\u0e48\u0e2d\u0e19\u0e08\u0e36\u0e07\u0e1b\u0e23\u0e31\u0e1a\u0e02\u0e19\u0e32\u0e14\u0e44\u0e14\u0e49")
SIZE_RANGE = (16, 48)
T_SCALE = "\u0e02\u0e19\u0e32\u0e14 %"
T_RESET = "\u0e04\u0e37\u0e19\u0e04\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
T_NOTE_APPROX = ("\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07\u0e40\u0e23\u0e34\u0e48\u0e21\u0e15\u0e49\u0e19\u0e43\u0e19"
                 "\u0e20\u0e32\u0e1e\u0e40\u0e1b\u0e47\u0e19\u0e04\u0e48\u0e32\u0e1b\u0e23\u0e30\u0e21\u0e32\u0e13")
T_FULLSCREEN = "\u0e40\u0e15\u0e47\u0e21\u0e2b\u0e19\u0e49\u0e32\u0e08\u0e2d (F11)"
T_PREVIEW = "\u0e14\u0e39\u0e15\u0e31\u0e27\u0e2d\u0e22\u0e48\u0e32\u0e07\u0e40\u0e15\u0e47\u0e21\u0e08\u0e2d (F5)"
T_PREVIEW_HINT = ("\u0e2d\u0e2d\u0e01\u0e08\u0e32\u0e01\u0e42\u0e2b\u0e21\u0e14\u0e40\u0e15\u0e47\u0e21\u0e08\u0e2d: Esc   "
                  "\u0e25\u0e32\u0e01\u0e01\u0e25\u0e48\u0e2d\u0e07\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e22\u0e49\u0e32\u0e22   "
                  "\u0e2a\u0e25\u0e31\u0e1a\u0e0b\u0e31\u0e1a\u0e23\u0e30\u0e2b\u0e27\u0e48\u0e32\u0e07\u0e40\u0e25\u0e48\u0e19/"
                  "\u0e09\u0e32\u0e01\u0e2a\u0e19\u0e17\u0e19\u0e32: Tab")
T_BACKGROUND = "\u0e1e\u0e37\u0e49\u0e19\u0e2b\u0e25\u0e31\u0e07"
BG_LABELS = {"photo1": "\u0e20\u0e32\u0e1e 1", "photo2": "\u0e20\u0e32\u0e1e 2",
             "gradient": "\u0e44\u0e25\u0e48\u0e2a\u0e35\u0e40\u0e14\u0e34\u0e21"}
T_CANCEL = "\u0e22\u0e01\u0e40\u0e25\u0e34\u0e01"
T_OK = "\u0e15\u0e01\u0e25\u0e07"

BG_TOP, BG_BOTTOM = (58, 66, 60), (18, 20, 22)
OUTLINES = {"sub": "#4FC3F7", "line": "#81C784", "choice": "#FFB74D"}
LABELS = {"sub": T_SUB, "line": T_LINE, "choice": T_CHOICES}
# option field prefix per preview item
FIELDS = {"sub": "sub", "line": "dialog", "choice": "choice"}
TAB_ITEMS = (("sub",), ("line", "choice"))


@dataclass
class Item:
    key: str
    image: ImageTk.PhotoImage | None = None
    width: int = 0
    height: int = 0
    # top-left of the box on the canvas when the offset is zero
    base_x: float = 0
    base_y: float = 0
    image_dx: float = 0


_photos: dict[str, Image.Image | None] = {}


def _photo(name: str) -> Image.Image | None:
    if name not in _photos:
        try:
            _photos[name] = Image.open(layout_background(name)).convert("RGB")
        except OSError:
            _photos[name] = None
    return _photos[name]


def _background(name: str, width: int, height: int) -> Image.Image:
    photo = _photo(name) if name != "gradient" else None
    if photo is not None:
        return photo.resize((width, height), Image.BILINEAR)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line([(0, y), (width, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    for i in range(1, 4):
        x, y = width * i // 4, height * i // 4
        draw.line([(x, 0), (x, height)], fill=(70, 78, 72))
        draw.line([(0, y), (width, y)], fill=(70, 78, 72))
    return img


def fit_16_9(width: int, height: int) -> tuple[int, int]:
    w = min(width, height * REF_W // REF_H)
    return max(160, w), max(90, w * REF_H // REF_W)


def _stack(rows: list[Image.Image], gap: int, align: str = "center") -> Image.Image:
    w = max(r.width for r in rows)
    h = sum(r.height for r in rows) + gap * (len(rows) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for r in rows:
        out.alpha_composite(r, ((w - r.width) // 2 if align == "center" else 0, y))
        y += r.height + gap
    return out


def clamp_offset(base: float, size: float, span: float, offset: float) -> float:
    """Offset in percent of `span`, limited so the box [base, base+size] stays inside [0, span]."""
    pos = min(max(base + offset * span / 100, 0), span - size)
    offset = min(max((pos - base) * 100 / span, -OFFSET_LIMIT), OFFSET_LIMIT)
    return round(offset * 2) / 2


class HudLayoutDialog(tk.Toplevel):
    def __init__(self, parent, opts: InstallOptions, on_save):
        super().__init__(parent)
        self.title(T_TITLE)
        self.transient(parent)
        self.minsize(640, 560)
        self.opts = opts
        self.cw, self.ch = CANVAS_W, CANVAS_H
        self.bg_name = opts.layout_bg if opts.layout_bg in LAYOUT_BGS else LAYOUT_BGS[0]
        self._resize_job = None
        self.preview_only = False
        self.on_save = on_save
        self.vars = {key: (tk.DoubleVar(value=getattr(opts, f"{field}_x")),
                           tk.DoubleVar(value=getattr(opts, f"{field}_y")))
                     for key, field in FIELDS.items()}
        self.v_sub_w = tk.IntVar(value=opts.sub_width)
        self.v_choice_scale = tk.IntVar(value=opts.choice_scale)
        self.v_sizes = (tk.IntVar(value=opts.size1), tk.IntVar(value=opts.size2))
        self.items = {key: Item(key) for key in FIELDS}
        self._drag = None
        self._syncing = False
        self._build()
        self._render_items()
        self.place_items()
        self.show_active()
        for vx, vy in self.vars.values():
            for var in (vx, vy):
                var.trace_add("write", lambda *_: self._on_var())
        self.v_sub_w.trace_add("write", lambda *_: self._on_width())
        for var in (*self.v_sizes, self.v_choice_scale):
            var.trace_add("write", lambda *_: self._on_width())
        self.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.bind("<F5>", lambda _e: self.toggle_preview())
        self.bind("<Escape>", lambda _e: self.exit_fullscreen())
        self.bind("<Tab>", self._next_tab)
        self.grab_set()

    # ---------- layout ----------
    def _build(self):
        self.root_frame = root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        self.top_bar = top = ttk.Frame(root)
        ttk.Label(top, text=T_HINT).pack(side="left")
        ttk.Button(top, text=T_PREVIEW, command=self.toggle_preview).pack(side="right")
        ttk.Button(top, text=T_FULLSCREEN, command=self.toggle_fullscreen).pack(side="right", padx=(0, 6))
        self.v_bg = tk.StringVar(value=BG_LABELS[self.bg_name])
        bg_box = ttk.Combobox(top, textvariable=self.v_bg, values=[BG_LABELS[n] for n in LAYOUT_BGS],
                              state="readonly", width=9)
        bg_box.pack(side="right", padx=(0, 10))
        bg_box.bind("<<ComboboxSelected>>", lambda _e: self._on_background())
        ttk.Label(top, text=T_BACKGROUND).pack(side="right", padx=(0, 4))

        self.stage = tk.Frame(root, bg=STAGE_BG, width=CANVAS_W, height=CANVAS_H)
        self.stage.bind("<Configure>", lambda _e: self._schedule_resize())
        self.canvas = tk.Canvas(self.stage, width=CANVAS_W, height=CANVAS_H, highlightthickness=0, bg=STAGE_BG)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self.bg_image = ImageTk.PhotoImage(_background(self.bg_name, self.cw, self.ch))
        self.canvas.create_image(0, 0, image=self.bg_image, anchor="nw", tags=("bg",))
        self.canvas.create_text(0, 0, anchor="n", fill="#cfd8dc", text=T_PREVIEW_HINT, font=ui(10),
                                tags=("overlay",), state="hidden")
        for key in FIELDS:
            color = OUTLINES[key]
            self.canvas.create_rectangle(0, 0, 0, 0, outline=color, dash=(4, 3), tags=(key, f"{key}_box"))
            self.canvas.create_image(0, 0, anchor="nw", tags=(key, f"{key}_img"))
            self.canvas.create_text(0, 0, anchor="sw", fill=color, text=LABELS[key], font=ui(8),
                                    tags=(key, f"{key}_label"))
            self.canvas.tag_bind(key, "<ButtonPress-1>", lambda e, k=key: self._drag_start(k, e))
            self.canvas.tag_bind(key, "<B1-Motion>", self._drag_move)
            self.canvas.tag_bind(key, "<ButtonRelease-1>", lambda _e: setattr(self, "_drag", None))
            self.canvas.tag_bind(key, "<Enter>", lambda _e: self.canvas.configure(cursor="fleur"))
            self.canvas.tag_bind(key, "<Leave>", lambda _e: self.canvas.configure(cursor=""))

        self.tabs = ttk.Notebook(root)

        sub = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(sub, text=T_SUB_TAB)
        vx, vy = self.vars["sub"]
        self._slider(sub, 0, T_X, vx, -OFFSET_LIMIT, OFFSET_LIMIT, 0.5)
        self._slider(sub, 1, T_Y, vy, -OFFSET_LIMIT, OFFSET_LIMIT, 0.5)
        self._slider(sub, 2, T_WIDTH, self.v_sub_w, WIDTH_RANGE[0], WIDTH_RANGE[1], 5)
        self._size_sliders(sub, 3)
        ttk.Button(sub, text=T_RESET, command=lambda: self.reset("sub")).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(6, 0))

        dlg = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(dlg, text=T_DIALOG_TAB)
        dlg.columnconfigure(0, weight=1)
        dlg.columnconfigure(1, weight=1)
        for col, key in enumerate(("line", "choice")):
            box = ttk.LabelFrame(dlg, text=LABELS[key], padding=6)
            box.grid(row=0, column=col, sticky="nsew", padx=(0, 4) if col == 0 else (4, 0))
            vx, vy = self.vars[key]
            self._slider(box, 0, T_X, vx, -OFFSET_LIMIT, OFFSET_LIMIT, 0.5)
            self._slider(box, 1, T_Y, vy, -OFFSET_LIMIT, OFFSET_LIMIT, 0.5)
            if key == "line":
                self._size_sliders(box, 2)
            else:
                self._slider(box, 2, T_SCALE, self.v_choice_scale, SCALE_RANGE[0], SCALE_RANGE[1], 5)
            ttk.Button(box, text=T_RESET, command=lambda k=key: self.reset(k)).grid(
                row=5, column=0, columnspan=3, sticky="nw", pady=(6, 0))
            box.rowconfigure(5, weight=1)

        self.tab_keys = {str(sub): TAB_ITEMS[0], str(dlg): TAB_ITEMS[1]}
        self.tabs.bind("<<NotebookTabChanged>>", lambda _e: self.show_active())

        self.note = ttk.Label(root, foreground=P.note, text=T_NOTE_APPROX)
        self.bottom = bottom = ttk.Frame(root)
        ttk.Button(bottom, text=T_CANCEL, command=self.destroy).pack(side="right")
        ttk.Button(bottom, text=T_OK, style="Big.TButton", command=self.save).pack(side="right", padx=(0, 6))
        self._pack_panels()

    def _pack_panels(self):
        for w in (self.top_bar, self.stage, self.tabs, self.note, self.bottom):
            w.pack_forget()
        if self.preview_only:
            self.root_frame.configure(padding=0)
            self.stage.pack(fill="both", expand=True)
            return
        self.root_frame.configure(padding=10)
        self.top_bar.pack(side="top", fill="x", pady=(0, 6))
        self.bottom.pack(side="bottom", fill="x", pady=(8, 0))
        self.note.pack(side="bottom", anchor="w", pady=(6, 0))
        self.tabs.pack(side="bottom", fill="x", pady=(8, 0))
        self.stage.pack(side="top", fill="both", expand=True)

    # ---------- window modes ----------
    def _set_fullscreen(self, on: bool):
        self.attributes("-fullscreen", on)
        if on:
            return
        # Windows hides a transient Toplevel when Tk restores its owner after fullscreen,
        # leaving the grab on an invisible window.
        self.update_idletasks()
        self.withdraw()
        self.deiconify()
        self.lift()
        self.focus_force()
        self.grab_set()

    def toggle_fullscreen(self):
        self._set_fullscreen(not self.attributes("-fullscreen"))

    def toggle_preview(self):
        self.preview_only = not self.preview_only
        self._set_fullscreen(self.preview_only)
        self._pack_panels()
        self.canvas.itemconfigure("overlay", state="normal" if self.preview_only else "hidden")
        self.canvas.tag_raise("overlay")

    def exit_fullscreen(self):
        if self.preview_only:
            self.toggle_preview()
        elif self.attributes("-fullscreen"):
            self._set_fullscreen(False)

    def _next_tab(self, _event):
        if not self.preview_only:
            return None
        tabs = self.tabs.tabs()
        self.tabs.select((tabs.index(self.tabs.select()) + 1) % len(tabs))
        return "break"

    def _schedule_resize(self):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(80, self._resize)

    def _refresh_background(self):
        self.bg_image = ImageTk.PhotoImage(_background(self.bg_name, self.cw, self.ch))
        self.canvas.itemconfigure("bg", image=self.bg_image)

    def _on_background(self):
        self.bg_name = next((n for n, label in BG_LABELS.items() if label == self.v_bg.get()), LAYOUT_BGS[0])
        self._refresh_background()

    def _resize(self):
        self._resize_job = None
        w, h = fit_16_9(self.stage.winfo_width(), self.stage.winfo_height())
        if (w, h) == (self.cw, self.ch):
            return
        self.cw, self.ch = w, h
        self.canvas.configure(width=w, height=h)
        self._refresh_background()
        self.canvas.coords("overlay", w / 2, 12)
        self.canvas.itemconfigure("overlay", font=ui(max(10, round(14 * self.k))))
        for key in FIELDS:
            self.canvas.itemconfigure(f"{key}_label", font=ui(max(8, round(12 * self.k))))
        self._render_items()
        self.place_items()

    def _slider(self, parent, row, label, var, lo, hi, step):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")

        def on_scale(value):
            snapped = round(float(value) / step) * step
            if isinstance(var, tk.IntVar):
                snapped = int(snapped)
            if self._safe_get(var) != snapped:
                var.set(snapped)

        def on_var(*_):
            value = self._safe_get(var)
            if value is not None:
                scale.set(value)
        scale = ttk.Scale(parent, from_=lo, to=hi, orient="horizontal", command=on_scale)
        scale.set(var.get())
        var.trace_add("write", on_var)
        scale.grid(row=row, column=1, sticky="ew", padx=6)
        spin = ttk.Spinbox(parent, from_=lo, to=hi, increment=step, textvariable=var, width=6)
        spin.grid(row=row, column=2)
        return scale, spin

    def _size_sliders(self, parent, row):
        widgets = []
        for i, (label, var) in enumerate(zip((T_SIZE1, T_SIZE2), self.v_sizes)):
            widgets += self._slider(parent, row + i, label, var, SIZE_RANGE[0], SIZE_RANGE[1], 1)
        if not self.opts.subtitle_style:
            for w in widgets:
                w.state(["disabled"])
            ttk.Label(parent, text=T_SIZE_OFF, foreground=P.note).grid(
                row=row + 2, column=0, columnspan=3, sticky="w")

    @staticmethod
    def _safe_get(var):
        try:
            return var.get()
        except (tk.TclError, ValueError):
            return None

    # ---------- rendering ----------
    @property
    def k(self) -> float:
        return self.cw / REF_W

    def _set_image(self, key: str, img: Image.Image, center_top: tuple[float, float], box_w: int | None = None):
        item = self.items[key]
        item.image = ImageTk.PhotoImage(img)
        item.width, item.height = max(box_w or 0, img.width), img.height
        item.base_x = center_top[0] * self.k - item.width / 2
        item.base_y = center_top[1] * self.k
        item.image_dx = (item.width - img.width) / 2

    def _sizes(self) -> tuple[int, int]:
        out = []
        for var, default in zip(self.v_sizes, (self.opts.size1, self.opts.size2)):
            value = self._safe_get(var)
            out.append(min(max(int(value), SIZE_RANGE[0]), SIZE_RANGE[1]) if value is not None else default)
        return out[0], out[1]

    def _render_items(self):
        size1, size2 = self._sizes()
        opts = replace(self.opts, size1=size1, size2=size2)
        line = subtitle_block(opts, self.k)

        box_w = round(SUB_BOX_W * self.k * self._width_pct() / 100)
        sub = subtitle_block(opts, self.k, max_width=box_w)
        last_px = (opts.size2 if opts.mode == MODE_DOUBLE else opts.size1) if opts.subtitle_style else 28
        bottom = SUB_BASELINE + descent_px(opts, last_px) + 1 / self.k
        self._set_image("sub", sub, (SUB_CENTER_X, bottom - sub.height / self.k), box_w)
        self._set_image("line", line, LINE_CENTER_TOP)

        img, left, bottom = self._choices_image(opts)
        self._set_image("choice", img, (left + img.width / self.k / 2, bottom - img.height / self.k))

    def _choices_image(self, opts: InstallOptions) -> tuple[Image.Image, float, float]:
        """Choice list image plus its left and bottom edge in 1920x1080 units."""
        s = CHOICE_BASE_SCALE * self._choice_pct() / 100
        u = s * self.k
        px = max(8, round(CHOICE_FONT * u))
        arrow_w = round(CHOICE_ARROW_W * u)
        options = []
        for i, (thai, english) in enumerate(CHOICES, 1):
            text = thai
            if opts.mode == MODE_DOUBLE:
                text = f"{thai} [{english}]" if opts.thai_first else f"{english} [{thai}]"
            rows = text_rows(opts, f"{i}. {text}", CHOICE_COLOR, px, CHOICE_FIELD_W * u)
            options.append(rows)
        line_h = max(1, round(CHOICE_LINE_H * u))
        gap = round(CHOICE_GAP * u)
        width = arrow_w + max(r.width for rows in options for r in rows)
        height = sum(len(rows) * line_h for rows in options) + gap * (len(options) - 1)
        out = Image.new("RGBA", (width, height + line_h), (0, 0, 0, 0))
        y = 0
        for n, rows in enumerate(options):
            if n == 0:
                cy = y + line_h / 2
                ImageDraw.Draw(out).polygon([(arrow_w * 0.15, cy - arrow_w * 0.35), (arrow_w * 0.75, cy),
                                             (arrow_w * 0.15, cy + arrow_w * 0.35)], fill=CHOICE_ARROW)
            for r in rows:
                out.alpha_composite(r, (arrow_w, max(0, y + (line_h - r.height) // 2)))
                y += line_h
            y += gap
        out = out.crop((0, 0, width, out.getbbox()[3] if out.getbbox() else height))
        left = CHOICE_ORIGIN[0] + (CHOICE_TEXT_X - CHOICE_ARROW_W) * s
        return out, left, CHOICE_ORIGIN[1] + CHOICE_BOTTOM * s

    def _width_pct(self) -> int:
        value = self._safe_get(self.v_sub_w)
        return min(max(int(value), WIDTH_RANGE[0]), WIDTH_RANGE[1]) if value is not None else 100

    def _choice_pct(self) -> int:
        value = self._safe_get(self.v_choice_scale)
        return min(max(int(value), SCALE_RANGE[0]), SCALE_RANGE[1]) if value is not None else 100

    def _clamp(self, item: Item, x: float, y: float) -> tuple[float, float]:
        return (clamp_offset(item.base_x, item.width, self.cw, x),
                clamp_offset(item.base_y, item.height, self.ch, y))

    def place_items(self):
        for key, item in self.items.items():
            vx, vy = self.vars[key]
            x, y = self._safe_get(vx), self._safe_get(vy)
            if x is None or y is None:
                continue
            cx, cy = self._clamp(item, x, y)
            if (cx, cy) != (x, y):
                self.after_idle(self._write_back, key, cx, cy)
            left = item.base_x + cx * self.cw / 100
            top = item.base_y + cy * self.ch / 100
            self.canvas.coords(f"{key}_box", left - 3, top - 3, left + item.width + 3, top + item.height + 3)
            self.canvas.itemconfigure(f"{key}_img", image=item.image)
            self.canvas.coords(f"{key}_img", left + item.image_dx, top)
            self.canvas.coords(f"{key}_label", left - 3, top - 4)

    def active(self) -> tuple[str, ...]:
        return self.tab_keys.get(self.tabs.select(), TAB_ITEMS[0])

    def show_active(self):
        active = self.active()
        for key in self.items:
            self.canvas.itemconfigure(key, state="normal" if key in active else "hidden")

    def _write_back(self, key, x, y):
        vx, vy = self.vars[key]
        if self._safe_get(vx) != x:
            vx.set(x)
        if self._safe_get(vy) != y:
            vy.set(y)

    def _on_var(self):
        if not self._syncing:
            self.place_items()

    def _on_width(self):
        if any(self._safe_get(v) is None for v in (self.v_sub_w, self.v_choice_scale, *self.v_sizes)):
            return
        self._render_items()
        self.place_items()

    # ---------- dragging ----------
    def _drag_start(self, key, event):
        self.canvas.tag_raise(key)
        vx, vy = self.vars[key]
        self._drag = (key, event.x, event.y, self._safe_get(vx) or 0.0, self._safe_get(vy) or 0.0)

    def _drag_move(self, event):
        if not self._drag:
            return
        key, sx, sy, ox, oy = self._drag
        x, y = self._clamp(self.items[key], ox + (event.x - sx) * 100 / self.cw,
                           oy + (event.y - sy) * 100 / self.ch)
        vx, vy = self.vars[key]
        self._syncing = True
        vx.set(x)
        self._syncing = False
        vy.set(y)

    # ---------- actions ----------
    def reset(self, key: str):
        vx, vy = self.vars[key]
        vx.set(0.0)
        vy.set(0.0)
        if key == "sub":
            self.v_sub_w.set(100)
        elif key == "choice":
            self.v_choice_scale.set(100)

    def values(self) -> dict:
        out = {}
        for key, field in FIELDS.items():
            vx, vy = self.vars[key]
            x, y = self._clamp(self.items[key], self._safe_get(vx) or 0.0, self._safe_get(vy) or 0.0)
            out[f"{field}_x"], out[f"{field}_y"] = float(x), float(y)
        out["sub_width"] = self._width_pct()
        out["choice_scale"] = self._choice_pct()
        out["layout_bg"] = self.bg_name
        if self.opts.subtitle_style:
            out["size1"], out["size2"] = self._sizes()
        return out

    def save(self):
        self.on_save(self.values())
        self.destroy()
