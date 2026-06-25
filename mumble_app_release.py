#!/usr/bin/env python3
"""
Mumble desktop wrapper — loads the hosted backend.
Replace MUMBLE_URL with your Railway URL after deploying.
"""
import os, sys
import webview

MUMBLE_URL = os.environ.get('MUMBLE_URL', 'https://web-production-5fe9a3.up.railway.app')

# macOS dock icon
try:
    from AppKit import NSApplication, NSImage
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon = os.path.join(base, 'MumbleIcon.icns')
    _app = NSApplication.sharedApplication()
    if os.path.exists(icon):
        _img = NSImage.alloc().initWithContentsOfFile_(icon)
        _app.setApplicationIconImage_(_img)
except Exception:
    pass

import platform, pathlib

# Persist browser state (mic permissions, login session) across restarts
_sys = platform.system()
if _sys == 'Darwin':
    STORAGE = str(pathlib.Path.home() / 'Library' / 'Application Support' / 'Mumble')
elif _sys == 'Windows':
    STORAGE = str(pathlib.Path.home() / 'AppData' / 'Local' / 'Mumble')
else:
    STORAGE = str(pathlib.Path.home() / '.config' / 'Mumble')
pathlib.Path(STORAGE).mkdir(parents=True, exist_ok=True)

window = webview.create_window(
    'Mumble',
    MUMBLE_URL,
    width=1100,
    height=720,
    resizable=True,
    min_size=(900, 600),
)
webview.start(private_mode=False, storage_path=STORAGE)
