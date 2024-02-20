# -*- mode: python ; coding: utf-8 -*-

import nicegui
from pathlib import Path

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[(str(Path(nicegui.__file__).parent), 'nicegui')],
    hiddenimports=['socketio'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'matplotlib', 'PIL', 'tcl', 'tk', 'tcl8'],
    noarchive=False,
)

EXCLUDED = [
    r"nicegui\elements\lib\mermaid",
    r"nicegui\elements\lib\echarts",
    r"nicegui\elements\lib\vanilla-jsoneditor",
    r"nicegui\elements\lib\aggrid",
    r"nicegui\elements\lib\three",
    r"nicegui\elements\lib\leaflet",
    r"nicegui\elements\lib\nipplejs"
]

a.datas = [k for k in a.datas if all(ex not in k[0] for ex in EXCLUDED)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='elecanalysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
