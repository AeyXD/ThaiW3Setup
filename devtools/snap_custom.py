import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageGrab
import ctypes
if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
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
    path = os.path.join(tmp, name)
    ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(path)
    print("saved", path, w, h)


def step1():
    grab(app, "w3thai_main.png")
    app.open_custom()
    app.after(1500, step2)


def step2():
    dlg = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"][0]
    dlg.tree.selection_set("2")
    dlg.toggle(2)
    grab(dlg, "w3thai_custom.png")
    dlg.destroy()
    app.destroy()


app.after(3000, step1)
app.mainloop()
