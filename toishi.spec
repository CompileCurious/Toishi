# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['toishi/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('toishi/frontend', 'frontend'),
        ('toishi/assets', 'assets'),
        ('Icon.ico', '.'),
    ],

    hiddenimports=[
        'pywebview.platforms.winforms',
        'clr',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Toishi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    icon='toishi/assets/Icon_win.ico',
    onefile=True,
)
