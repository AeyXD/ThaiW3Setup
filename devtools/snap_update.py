"""Pretend to be an old version and capture the update banner and dialog."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageGrab
import ctypes
if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
import core.update
import gui.update_dialog
core.update.__version__ = gui.update_dialog.__version__ = "0.0.1"
import gui.app as appmod

tmp = tempfile.gettempdir()
app = appmod.App()


def grab(win, name):
    win.attributes("-topmost", True)
    win.lift()
    win.update()
    win.after(400)
    win.update()
    x, y, w, h = win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(os.path.join(tmp, name))
    print("saved", name, w, h)


def step1():
    print("banner:", app.banner is not None and app.banner.winfo_exists())
    grab(app, "w3thai_update_main.png")
    app.check_update(manual=True)
    app.after(4000, step2)


def step2():
    dlg = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"]
    if dlg:
        grab(dlg[0], "w3thai_update_dialog.png")
    print("status:", ascii(app.v_status.get()))
    app.destroy()


app.after(6000, step1)
app.mainloop()
