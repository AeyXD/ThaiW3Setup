import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageGrab
import ctypes
if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
from gui.app import App

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "w3thai_gui.png")
mode = sys.argv[2] if len(sys.argv) > 2 else ""
app = App()
if mode == "double":
    app.v_mode.set("double")
    app.v_color1.set("#FFE08A")
    app.v_size2.set(24)


def snap():
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(out)
    print("saved", out, w, h)
    app.destroy()


app.after(3500, snap)
app.mainloop()
