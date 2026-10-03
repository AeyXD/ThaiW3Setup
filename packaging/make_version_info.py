"""Write packaging/version_info.txt for PyInstaller from core.__version__."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import APP_NAME, __version__  # noqa: E402

parts = [int(p) for p in re.findall(r"\d+", __version__)] + [0] * 4
ver = tuple(parts[:4])

TEMPLATE = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={ver}, prodvers={ver}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Witcher 3 Thai Community'),
      StringStruct('FileDescription', 'Thai translation installer for The Witcher 3 Remastered'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('LegalCopyright', 'MIT License. Translation by the w3tu / Kuntoon team.'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

out = os.path.join(os.path.dirname(__file__), "version_info.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write(TEMPLATE)
print("wrote", out, __version__)
