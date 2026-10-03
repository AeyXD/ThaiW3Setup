import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

import gui.app as appmod
from gui.hud_layout_dialog import HudLayoutDialog

user32 = ctypes.windll.user32
GW_OWNER = 4


class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]


def hwnd(w):
    return user32.GetParent(w.winfo_id()) or w.winfo_id()


def above(a, b):
    """True if window a is above window b in z-order."""
    h = user32.GetWindow(b, 3)  # GW_HWNDPREV
    while h:
        if h == a:
            return True
        h = user32.GetWindow(h, 3)
    return False


def state(app, dlg, tag):
    dlg.update()
    h = hwnd(dlg)
    r = RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    print(f"{tag:10} visible={user32.IsWindowVisible(h)} iconic={user32.IsIconic(h)} "
          f"above_main={above(h, hwnd(app))} owner={user32.GetWindow(h, GW_OWNER) == hwnd(app)} "
          f"rect=({r.l},{r.t},{r.r},{r.b}) fs={dlg.attributes('-fullscreen')}")


app = appmod.App()
app.update()
dlg = HudLayoutDialog(app, app.current_options(), lambda v: None)
state(app, dlg, "open")
for mode in sys.argv[1:] or ["f11", "f5"]:
    dlg.focus_force()
    dlg.event_generate("<F11>" if mode == "f11" else "<F5>")
    dlg.after(400)
    state(app, dlg, f"{mode} on")
    dlg.event_generate("<Escape>")
    dlg.after(400)
    state(app, dlg, f"{mode} esc")
app.destroy()
