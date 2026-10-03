"""Preview and send a problem report (see core/report.py)."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from core.report import collect_details, compose_report, format_contact, report_url, send_report
from gui.theme import P, mono, ui

log = logging.getLogger(__name__)

T_TITLE = "\u0e2a\u0e48\u0e07\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19\u0e1b\u0e31\u0e0d\u0e2b\u0e32"
T_INTRO = ("\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e14\u0e49\u0e32\u0e19\u0e25\u0e48\u0e32\u0e07\u0e08\u0e30\u0e16\u0e39\u0e01"
           "\u0e2a\u0e48\u0e07\u0e43\u0e2b\u0e49\u0e1c\u0e39\u0e49\u0e1e\u0e31\u0e12\u0e19\u0e32\u0e40\u0e1e\u0e37\u0e48\u0e2d"
           "\u0e0a\u0e48\u0e27\u0e22\u0e2b\u0e32\u0e2a\u0e32\u0e40\u0e2b\u0e15\u0e38\n\u0e44\u0e21\u0e48\u0e15\u0e49\u0e2d\u0e07 login "
           "\u0e41\u0e25\u0e30\u0e0a\u0e37\u0e48\u0e2d\u0e1c\u0e39\u0e49\u0e43\u0e0a\u0e49 Windows "
           "\u0e16\u0e39\u0e01\u0e0b\u0e48\u0e2d\u0e19\u0e44\u0e27\u0e49\u0e41\u0e25\u0e49\u0e27")
T_NOTE = ("\u0e2d\u0e18\u0e34\u0e1a\u0e32\u0e22\u0e1b\u0e31\u0e0d\u0e2b\u0e32\u0e2a\u0e31\u0e49\u0e19 \u0e46 "
          "(\u0e44\u0e21\u0e48\u0e1a\u0e31\u0e07\u0e04\u0e31\u0e1a):")
T_SEND = "\u0e2a\u0e48\u0e07\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19"
T_COPY = "\u0e04\u0e31\u0e14\u0e25\u0e2d\u0e01"
T_CLOSE = "\u0e1b\u0e34\u0e14"
T_SENDING = "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e2a\u0e48\u0e07..."
T_SENT = "\u0e2a\u0e48\u0e07\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19\u0e41\u0e25\u0e49\u0e27 \u0e23\u0e2b\u0e31\u0e2a\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19:"
T_SENT_HINT = ("\u0e04\u0e31\u0e14\u0e25\u0e2d\u0e01\u0e23\u0e2b\u0e31\u0e2a\u0e44\u0e27\u0e49\u0e41\u0e25\u0e49\u0e27 "
               "\u0e41\u0e08\u0e49\u0e07\u0e23\u0e2b\u0e31\u0e2a\u0e19\u0e35\u0e49\u0e15\u0e2d\u0e19\u0e2a\u0e2d\u0e1a\u0e16\u0e32\u0e21"
               "\u0e43\u0e19\u0e01\u0e25\u0e38\u0e48\u0e21")
T_FAILED = "\u0e2a\u0e48\u0e07\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19\u0e44\u0e21\u0e48\u0e2a\u0e33\u0e40\u0e23\u0e47\u0e08:"
T_FAILED_HINT = ("\u0e04\u0e31\u0e14\u0e25\u0e2d\u0e01\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19\u0e44\u0e27\u0e49\u0e41\u0e25\u0e49\u0e27 "
                 "\u0e27\u0e32\u0e07\u0e2a\u0e48\u0e07\u0e43\u0e19\u0e01\u0e25\u0e38\u0e48\u0e21\u0e41\u0e17\u0e19\u0e44\u0e14\u0e49")
T_COPIED = "\u0e04\u0e31\u0e14\u0e25\u0e2d\u0e01\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19\u0e41\u0e25\u0e49\u0e27"
T_OFFLINE = ("\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e30\u0e1a\u0e1a\u0e2a\u0e48\u0e07"
             "\u0e23\u0e32\u0e22\u0e07\u0e32\u0e19 \u0e01\u0e14 \u0e04\u0e31\u0e14\u0e25\u0e2d\u0e01 "
             "\u0e41\u0e25\u0e49\u0e27\u0e27\u0e32\u0e07\u0e2a\u0e48\u0e07\u0e43\u0e19\u0e01\u0e25\u0e38\u0e48\u0e21\u0e41\u0e17\u0e19")
T_CONTACT_TITLE = "ต้องการให้เราติดต่อกลับไหม?"
T_CONTACT_WANT = "ต้องการให้ผู้พัฒนาติดต่อกลับ"
T_CONTACT_KIND = "ช่องทาง"
T_CONTACT_HINT = "ใส่ชื่อผู้ใช้ ลิงก์โปรไฟล์ หรืออีเมล ใช้ติดต่อเรื่องรายงานนี้เท่านั้น"
T_CONTACT_MISSING = "ยังไม่ได้ใส่ช่องทางติดต่อ\nส่งรายงานโดยไม่ให้ติดต่อกลับหรือไม่?"
T_CONTACT_REPLY = "เราจะติดต่อกลับทาง"
T_SHOW_PREVIEW = "▸ ดูข้อมูลที่จะส่ง"
T_HIDE_PREVIEW = "▾ ซ่อนข้อมูลที่จะส่ง"
CONTACT_KINDS = ("Facebook", "Discord", "LINE", "Email", "อื่น ๆ")
CONTACT_OTHER = "other"
T_COLLECTING = "กำลังรวบรวมข้อมูลเกม..."
TEXT_W = 600
PREVIEW_ROW = 5
REFRESH_MS = 250
POLL_MS = 100


class ReportDialog(tk.Toplevel):
    def __init__(self, parent, game_path: str):
        super().__init__(parent)
        self.title(T_TITLE)
        self.transient(parent)
        self.minsize(640, 1)
        self.game_path = game_path
        self.events: queue.Queue = queue.Queue()
        style = ttk.Style(self)
        style.configure("Contact.TLabelframe.Label", font=ui(12, "bold"), foreground=P.accent)
        style.configure("Hint.TLabel", font=ui(9), foreground=P.hint)

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        self.root_frame = root
        ttk.Label(root, text=T_INTRO, wraplength=TEXT_W, justify="left").grid(row=0, column=0, sticky="w")

        contact = ttk.LabelFrame(root, text=T_CONTACT_TITLE, style="Contact.TLabelframe", padding=10)
        contact.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        contact.columnconfigure(2, weight=1)
        self.v_want = tk.BooleanVar(value=False)
        self.v_kind = tk.StringVar(value=CONTACT_KINDS[0])
        self.v_contact = tk.StringVar()
        ttk.Checkbutton(contact, text=T_CONTACT_WANT, variable=self.v_want, command=self.update_contact).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(contact, text=T_CONTACT_KIND).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.cb_kind = ttk.Combobox(contact, textvariable=self.v_kind, values=CONTACT_KINDS, width=10)
        self.cb_kind.grid(row=1, column=1, sticky="w", padx=(6, 6), pady=(6, 0))
        self.cb_kind.bind("<<ComboboxSelected>>", lambda _e: self.schedule_refresh())
        self.ent_contact = ttk.Entry(contact, textvariable=self.v_contact, font=ui(10))
        self.ent_contact.grid(row=1, column=2, sticky="ew", pady=(6, 0))
        self.ent_contact.bind("<KeyRelease>", lambda _e: self.schedule_refresh())
        ttk.Label(contact, text=T_CONTACT_HINT, style="Hint.TLabel").grid(row=2, column=0, columnspan=3, sticky="w",
                                                                         pady=(4, 0))

        ttk.Label(root, text=T_NOTE).grid(row=2, column=0, sticky="w", pady=(10, 2))
        self.note = tk.Text(root, height=3, wrap="word", font=ui(10))
        self.note.grid(row=3, column=0, sticky="ew")
        self.note.bind("<KeyRelease>", lambda _e: self.schedule_refresh())

        self.btn_preview = ttk.Button(root, text=T_SHOW_PREVIEW, command=self.toggle_preview)
        self.btn_preview.grid(row=4, column=0, sticky="w", pady=(10, 0))
        frame = ttk.Frame(root)
        self.preview_frame = frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.preview = tk.Text(frame, height=18, wrap="none", font=mono(9))
        self.preview.grid(row=0, column=0, sticky="nsew")
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.preview.yview)
        ys.grid(row=0, column=1, sticky="ns")
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.preview.xview)
        xs.grid(row=1, column=0, sticky="ew")
        self.preview.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)

        bottom = ttk.Frame(root)
        bottom.grid(row=PREVIEW_ROW + 1, column=0, sticky="ew", pady=(10, 0))
        self.status = tk.StringVar(value="" if report_url() else T_OFFLINE)
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        ttk.Button(bottom, text=T_CLOSE, command=self.destroy).pack(side="right")
        self.btn_copy = ttk.Button(bottom, text=T_COPY, command=self.copy)
        self.btn_copy.pack(side="right", padx=(0, 4))
        self.btn_send = ttk.Button(bottom, text=T_SEND, style="Big.TButton", command=self.send)
        self.btn_send.pack(side="right", padx=(0, 4))
        self.btn_send.state(["disabled"])
        self.btn_copy.state(["disabled"])

        self._refresh_job = None
        self.text = ""
        self.details: str | None = None
        self.update_contact()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        self.note.focus_set()
        self.collect()
        self.after(POLL_MS, self._poll)

    def collect(self):
        self.status.set(T_COLLECTING)
        game_path = self.game_path

        def work():
            try:
                self.events.put(("details", collect_details(game_path)))
            except Exception as exc:  # a broken game folder must not block sending the note
                log.exception("collecting report details failed")
                self.events.put(("details_error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def schedule_refresh(self):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(REFRESH_MS, self.refresh)

    def contact(self) -> str:
        if not self.v_want.get():
            return ""
        kind = self.v_kind.get()
        return format_contact(CONTACT_OTHER if kind == CONTACT_KINDS[-1] else kind, self.v_contact.get())

    def update_contact(self):
        want = self.v_want.get()
        self.cb_kind.configure(state="readonly" if want else "disabled")
        self.ent_contact.configure(state="normal" if want else "disabled")
        if want:
            self.ent_contact.focus_set()
        self.schedule_refresh()

    def toggle_preview(self):
        if self.preview_frame.winfo_ismapped():
            self.preview_frame.grid_remove()
            self.root_frame.rowconfigure(PREVIEW_ROW, weight=0)
            self.btn_preview.configure(text=T_SHOW_PREVIEW)
        else:
            self.preview_frame.grid(row=PREVIEW_ROW, column=0, sticky="nsew", pady=(6, 0))
            self.root_frame.rowconfigure(PREVIEW_ROW, weight=1)
            self.btn_preview.configure(text=T_HIDE_PREVIEW)
            self.show_preview()
        self.geometry("")

    def refresh(self):
        self._refresh_job = None
        if self.details is None:
            return
        self.text = compose_report(self.details, self.note.get("1.0", "end"), self.contact())
        if self.preview_frame.winfo_ismapped():
            self.show_preview()

    def show_preview(self):
        top = self.preview.yview()[0]
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", self.text or T_COLLECTING)
        self.preview.configure(state="disabled")
        self.preview.yview_moveto(top)

    def on_details(self, details: str):
        self.details = details
        self.status.set("" if report_url() else T_OFFLINE)
        self.btn_copy.state(["!disabled"])
        if report_url():
            self.btn_send.state(["!disabled"])
        self.refresh()

    def _clip(self, value: str):
        self.clipboard_clear()
        self.clipboard_append(value)

    def copy(self):
        self.refresh()
        self._clip(self.text)
        self.status.set(T_COPIED)

    def send(self):
        self.refresh()
        if self.v_want.get() and not self.contact():
            if not messagebox.askyesno(T_TITLE, T_CONTACT_MISSING, parent=self):
                self.ent_contact.focus_set()
                return
        self.sent_contact = self.contact()
        self.btn_send.state(["disabled"])
        self.status.set(T_SENDING)
        text = self.text

        def work():
            try:
                self.events.put(("ok", send_report(text)))
            except Exception as exc:  # network errors come in many types
                log.warning("report upload failed: %s", exc)
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            while True:
                self._handle(*self.events.get_nowait())
        except queue.Empty:
            pass
        self.after(POLL_MS, self._poll)

    def _handle(self, kind: str, value: str):
        if kind == "details":
            self.on_details(value)
            return
        if kind == "details_error":
            self.on_details(f"(collecting game details failed: {value})")
            return
        self.btn_send.state(["!disabled"])
        if kind == "ok":
            self._clip(value)
            self.status.set(f"{T_SENT} {value}")
            reply = f"\n{T_CONTACT_REPLY} {self.sent_contact}" if self.sent_contact else ""
            messagebox.showinfo(T_TITLE, f"{T_SENT} {value}\n{T_SENT_HINT}{reply}", parent=self)
        else:
            self._clip(self.text)
            self.status.set("")
            messagebox.showerror(T_TITLE, f"{T_FAILED} {value}\n{T_FAILED_HINT}", parent=self)
