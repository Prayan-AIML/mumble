#!/usr/bin/env python3
import os, sys, threading, time

# Run from the app's own directory so server.py finds index.html and .env.local
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'Mumble.app', 'Contents', 'Resources', 'MumbleIcon.icns')

# Set dock icon via AppKit before anything else loads
try:
    from AppKit import NSApplication, NSImage
    _app = NSApplication.sharedApplication()
    if os.path.exists(ICON_PATH):
        _img = NSImage.alloc().initWithContentsOfFile_(ICON_PATH)
        _app.setApplicationIconImage_(_img)
except Exception:
    pass

import server

def run_server():
    server.start()

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(1.5)  # wait for server to be ready

import webview

STORAGE = os.path.expanduser('~/Library/Application Support/Mumble')
os.makedirs(STORAGE, exist_ok=True)

window = webview.create_window(
    'Mumble',
    'http://localhost:3456',
    width=1100,
    height=720,
    resizable=True,
    min_size=(900, 600),
)
webview.start(
    icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
    private_mode=False,
    storage_path=STORAGE,
)
