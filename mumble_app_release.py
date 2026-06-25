#!/usr/bin/env python3
import os, sys, platform, pathlib
import webview
from mic_api import MicAPI

MUMBLE_URL = os.environ.get('MUMBLE_URL', 'https://web-production-5fe9a3.up.railway.app')

# macOS dock icon
try:
    from AppKit import NSApplication, NSImage
    _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    _icon = os.path.join(_base, 'MumbleIcon.icns')
    _app = NSApplication.sharedApplication()
    if os.path.exists(_icon):
        _img = NSImage.alloc().initWithContentsOfFile_(_icon)
        _app.setApplicationIconImage_(_img)
except Exception:
    pass

# Persist session (login, permissions) across restarts
_sys = platform.system()
if _sys == 'Darwin':
    STORAGE = str(pathlib.Path.home() / 'Library' / 'Application Support' / 'Mumble')
elif _sys == 'Windows':
    STORAGE = str(pathlib.Path.home() / 'AppData' / 'Local' / 'Mumble')
else:
    STORAGE = str(pathlib.Path.home() / '.config' / 'Mumble')
pathlib.Path(STORAGE).mkdir(parents=True, exist_ok=True)

_mic = MicAPI()

window = webview.create_window(
    'Mumble',
    MUMBLE_URL,
    width=1100,
    height=720,
    resizable=True,
    min_size=(900, 600),
    js_api=_mic,
)
webview.start(private_mode=False, storage_path=STORAGE)
