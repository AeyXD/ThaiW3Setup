# PyInstaller spec: onedir, windowed, no UPX (UPX-packed exes trigger antivirus heuristics).
# -*- mode: python ; coding: utf-8 -*-
import sys

sys.path.insert(0, SPECPATH)
from core import APP_NAME, APP_TITLE, __version__

MACOS = sys.platform == "darwin"
BUNDLE_ID = "io.github.fordenhillson.thaiw3setup"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets")],
    hiddenimports=["PIL._tkinter_finder"],
    excludes=["numpy", "pandas", "matplotlib", "scipy", "IPython", "pytest", "unittest", "pydoc",
              "lxml", "PIL.ImageQt", "PyQt5", "PySide2", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    uac_admin=False,
    icon="packaging/icon.icns" if MACOS else "packaging/icon.ico",
    # version_info is a Windows resource; macOS carries the same numbers in Info.plist below
    version=None if MACOS else "packaging/version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

if MACOS:
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon="packaging/icon.icns",
        bundle_identifier=BUNDLE_ID,
        version=__version__,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "NSHumanReadableCopyright": APP_TITLE,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.utilities",
        },
    )
