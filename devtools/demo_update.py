"""Open the real GUI pretending to be an old version, to preview the update banner and dialog."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import ctypes

if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
import core.update
import gui.update_dialog

core.update.__version__ = gui.update_dialog.__version__ = "0.0.1"
import gui.app as appmod

app = appmod.App()
app.after(4000, lambda: app.check_update(manual=True))
app.mainloop()
