# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['aogetapp.py'],
    pathex=['config', 'controller', 'db', 'model', 'util', 'view', 'web'],
    binaries=[],
    datas=[('resources', 'resources'), ('qt', 'qt')],
    hiddenimports=['config', 'controller', 'db', 'model', 'util', 'view', 'web'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='aoget',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\icons\\download.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='aoget',
)
