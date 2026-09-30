"""Preview and send a problem report (see core/report.py)."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from core.report import build_report, report_url, send_report

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
TEXT_W = 600


class ReportDialog(tk.Toplevel):
    def __init__(self, parent, game_path: str):
        super().__init__(parent)
        self.title(T_TITLE)
        self.transient(parent)
        self.minsize(640, 420)
        self.game_path = game_path
        self.events: queue.Queue = queue.Queue()

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)
        ttk.Label(root, text=T_INTRO, wraplength=TEXT_W, justify="left").grid(row=0, column=0, sticky="w")
        ttk.Label(root, text=T_NOTE).grid(row=1, column=0, sticky="w", pady=(10, 2))
        self.note = tk.Text(root, height=3, wrap="word", font=("Leelawadee UI", 10))
        self.note.grid(row=2, column=0, sticky="ew")
        self.note.bind("<KeyRelease>", lambda _e: self.schedule_refresh())

        frame = ttk.Frame(root)
        frame.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.preview = tk.Text(frame, height=18, wrap="none", font=("Consolas", 9))
        self.preview.grid(row=0, column=0, sticky="nsew")
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.preview.yview)
        ys.grid(row=0, column=1, sticky="ns")
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.preview.xview)
        xs.grid(row=1, column=0, sticky="ew")
        self.preview.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)

        bottom = ttk.Frame(root)
        bottom.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self.status = tk.StringVar(value="" if report_url() else T_OFFLINE)
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        ttk.Button(bottom, text=T_CLOSE, command=self.destroy).pack(side="right")
        ttk.Button(bottom, text=T_COPY, command=self.copy).pack(side="right", padx=(0, 4))
        self.btn_send = ttk.Button(bottom, text=T_SEND, style="Big.TButton", command=self.send)
        self.btn_send.pack(side="right", padx=(0, 4))
        if not report_url():
            self.btn_send.state(["disabled"])

        self._refresh_job = None
        self.text = ""
        self.refresh()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        self.note.focus_set()

    def schedule_refresh(self):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(600, self.refresh)

    def refresh(self):
        self._refresh_job = None
        self.text = build_report(self.game_path, self.note.get("1.0", "end"))
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", self.text)
        self.preview.configure(state="disabled")

    def _clip(self, value: str):
        self.clipboard_clear()
        self.clipboard_append(value)

    def copy(self):
        self.refresh()
        self._clip(self.text)
        self.status.set(T_COPIED)

    def send(self):
        self.refresh()
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
        self.after(200, self._poll)

    def _poll(self):
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            if self.winfo_exists():
                self.after(200, self._poll)
            return
        self.btn_send.state(["!disabled"])
        if kind == "ok":
            self._clip(value)
            self.status.set(f"{T_SENT} {value}")
            messagebox.showinfo(T_TITLE, f"{T_SENT} {value}\n{T_SENT_HINT}", parent=self)
        else:
            self._clip(self.text)
            self.status.set("")
            messagebox.showerror(T_TITLE, f"{T_FAILED} {value}\n{T_FAILED_HINT}", parent=self)
