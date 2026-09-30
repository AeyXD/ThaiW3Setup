"""Screenshot the main window pointed at a fake 5.0 install with content1-content12 left over."""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from PIL import ImageGrab
from core import game_detect

game = Path(tempfile.mkdtemp()) / "The Witcher 3"
for i in range(13):
    (game / "content" / f"content{i}").mkdir(parents=True)
(game / "bin" / "x64_dx12").mkdir(parents=True)
(game / "bin" / "x64_dx12" / "witcher3.exe").write_bytes(b"")
game_detect.exe_version = lambda _p: "5.0.15.58680"

from gui import app as app_mod
win = app_mod.App()
win.v_game.set(str(game))


def snap():
    win.refresh_game()
    win.update()
    x, y = win.winfo_rootx(), win.winfo_rooty()
    ImageGrab.grab((x, y, x + win.winfo_width(), y + 260)).save(os.path.join(tempfile.gettempdir(), "stale_snap.png"))
    win.destroy()
    shutil.rmtree(game.parent, ignore_errors=True)


win.after(2500, snap)
win.mainloop()
print(os.path.join(tempfile.gettempdir(), "stale_snap.png"))
