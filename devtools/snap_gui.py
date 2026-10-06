import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageGrab
import ctypes
if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
from gui.app import App

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "w3thai_gui.png")
mode = sys.argv[2] if len(sys.argv) > 2 else ""
tab = int(sys.argv[3]) if len(sys.argv) > 3 else 0
App.show_upgrade_notice = lambda self: None
app = App()
app.after(500, lambda: app.notebook.select(tab))
if mode == "double":
    app.v_mode.set("double")
    app.v_color1.set("#FFE08A")
    app.v_size2.set(24)
if mode == "names":
    app.set_all_names(True)
    app.set_all_name_modes("double")
    app.v_tab_modes[sorted(app.v_tab_modes)[0]].set("\u0e44\u0e17\u0e22")


def snap():
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(out)
    print("saved", out, w, h)
    app.destroy()


app.after(3500, snap)
app.mainloop()
