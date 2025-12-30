# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PMU-30 Configurator
Creates a portable single-folder distribution with all dependencies included
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Project paths
project_dir = os.path.abspath(os.path.dirname(SPEC))
src_dir = os.path.join(project_dir, 'src')

# Collect all submodules for packages that need it
hidden_imports = [
    # PyQt6 modules
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',
    'PyQt6.QtNetwork',

    # Serial communication
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.list_ports_windows',

    # CAN tools
    'can',
    'cantools',

    # Plotting
    'pyqtgraph',
    'pyqtgraph.graphicsItems',
    'pyqtgraph.widgets',
    'numpy',

    # Data formats
    'yaml',
    'json5',
    'pydantic',

    # Networking
    'websockets',
    'requests',

    # Application modules
    'ui',
    'ui.main_window_professional',
    'ui.tabs',
    'ui.widgets',
    'ui.dialogs',
    'controllers',
    'communication',
    'models',
    'utils',
]

# Collect data files from packages
datas = []

# Add pyqtgraph data files
try:
    datas += collect_data_files('pyqtgraph')
except Exception:
    pass

# Add cantools data files (DBC templates, etc)
try:
    datas += collect_data_files('cantools')
except Exception:
    pass

# Analysis configuration
a = Analysis(
    [os.path.join(src_dir, 'main.py')],
    pathex=[src_dir, project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(project_dir, 'runtime_hook.py')],
    excludes=[
        # Exclude development tools
        'black',
        'pylint',
        'pytest',
        'pytest_qt',
        'pyinstaller',
        # Exclude unused modules
        'tkinter',
        'matplotlib',
        'IPython',
        'notebook',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate binaries and datas
a.binaries = list(set(a.binaries))
a.datas = list(set(a.datas))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PMU-30 Configurator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available: 'assets/icon.ico'
    version='version_info.txt',  # Windows version info
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PMU-30_Configurator',
)
