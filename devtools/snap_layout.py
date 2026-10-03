import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageGrab
import ctypes
if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
import gui.app as appmod
from gui.hud_layout_dialog import BG_LABELS

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
    app.v_style.set(True)
    grab(app, "w3thai_main.png")
    app.open_layout()
    app.after(1500, step2)


def step2():
    dlg = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"][0]
    grab(dlg, "w3thai_layout_default.png")
    for name in ("photo2", "gradient", "photo1"):
        dlg.v_bg.set(BG_LABELS[name])
        dlg._on_background()
        grab(dlg, f"w3thai_layout_bg_{name}.png")
    dlg.vars["sub"][1].set(-20)
    dlg.v_sub_w.set(80)
    grab(dlg, "w3thai_layout_moved.png")
    dlg.tabs.select(1)
    grab(dlg, "w3thai_layout_dialog_tab.png")
    dlg.vars["line"][1].set(-40)
    dlg.vars["choice"][0].set(-30)
    dlg.vars["choice"][1].set(90)
    grab(dlg, "w3thai_layout_dialog_moved.png")
    dlg.v_sizes[0].set(44)
    dlg.v_sizes[1].set(20)
    grab(dlg, "w3thai_layout_sizes.png")
    print("values", dlg.values())
    dlg.toggle_preview()
    app.after(1200, lambda: step3(dlg))


def step3(dlg):
    grab(dlg, "w3thai_layout_preview_full.png")
    dlg.exit_fullscreen()
    dlg.toggle_fullscreen()
    app.after(1200, lambda: step4(dlg))


def step4(dlg):
    grab(dlg, "w3thai_layout_fullscreen.png")
    dlg.destroy()
    app.destroy()


app.after(3000, step1)
app.mainloop()
