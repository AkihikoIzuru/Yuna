# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Yuna."""

import os
import sys
from pathlib import Path

# Use the project root - the spec is run from the project root directory
base_path = Path.cwd()
block_cipher = None

# Collect datas
datas = []

# Add voice models directory (downloaded at runtime, but include if exists)
voice_models = base_path / "yuna" / "voice" / "models"
if voice_models.exists():
    datas.append((str(voice_models), "yuna/voice/models"))

# Add UI static files
ui_static = base_path / "yuna" / "ui" / "static"
if ui_static.exists():
    datas.append((str(ui_static), "yuna/ui/static"))

# Add home icon if exists
home_icon = base_path / "yuna" / "app" / "icons"
if home_icon.exists():
    datas.append((str(home_icon), "yuna/app/icons"))

a = Analysis(
    [str(base_path / 'yuna/main.py')],
    pathex=[str(base_path)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'faster_whisper',
        'onnxruntime',
        'pystray',
        'webview',
        'keyring',
        'pynput',
        'uvicorn',
        'starlette',
        'yuna.app',
        'yuna.app.tray',
        'yuna.app.window',
        'yuna.app.lifecycle',
        'yuna.app.hotkeys',
        'yuna.app.notify',
        'yuna.app.secrets',
        'yuna.app.autostart',
        'yuna.app.icons',
        'yuna.ui.server',
        'yuna.voice.loop',
        'yuna.voice.stt',
        'yuna.voice.tts',
        'yuna.voice.wake',
        'yuna.brain.agent',
        'yuna.brain.prompts',
        'yuna.tools.registry',
        'yuna.tools.system',
        'yuna.tools.memory',
        'yuna.tools.home',
        'yuna.memory',
        'yuna.memory.db',
        'yuna.memory.conversation',
        'yuna.memory.facts',
        'yuna.memory.reminders',
        'yuna.home',
        'yuna.home.ha',
        'yuna.home.mqtt',
        'yuna.home.mikrotik',
        'yuna.home.alerts',
        'yuna.safety',
        'yuna.safety.policy',
        'edge_tts',
        'sounddevice',
        'numpy',
        'scipy',
    ],
    exclude_modules=['webrtcvad', '_pyinstaller_hooks_0_webrtcvad'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Yuna',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Yuna',
)