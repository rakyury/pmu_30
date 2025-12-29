# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('pyqtgraph')
datas += collect_data_files('cantools')


a = Analysis(
    ['C:\\Projects\\pmu_30\\configurator\\src\\main.py'],
    pathex=['C:\\Projects\\pmu_30\\configurator\\src', 'C:\\Projects\\pmu_30\\configurator'],
    binaries=[],
    datas=datas,
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg', 'PyQt6.QtNetwork', 'serial', 'serial.tools', 'serial.tools.list_ports', 'serial.tools.list_ports_windows', 'can', 'cantools', 'pyqtgraph', 'numpy', 'yaml', 'json5', 'pydantic', 'websockets', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['C:\\Projects\\pmu_30\\configurator\\runtime_hook.py'],
    excludes=['black', 'pylint', 'pytest', 'pytest_qt', 'tkinter', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PMU-30 Configurator',
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
    version='C:\\Projects\\pmu_30\\configurator\\version_info.txt',
)
