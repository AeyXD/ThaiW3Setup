# PyInstaller spec: onedir, windowed, no UPX (UPX-packed exes trigger antivirus heuristics).
# -*- mode: python ; coding: utf-8 -*-

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
    name="ThaiW3Setup",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    uac_admin=False,
    icon="packaging/icon.ico",
    version="packaging/version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ThaiW3Setup",
)
