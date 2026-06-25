#!/usr/bin/env python3
import os, sys, threading, time, base64, io, wave
import numpy as np
import sounddevice as sd

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

class MicAPI:
    def __init__(self):
        self._stream = None
        self._chunks = []
        self._recording = False

    def start(self):
        self._chunks = []
        self._recording = True
        def cb(indata, frames, t, status):
            if self._recording:
                self._chunks.append(indata.copy())
        self._stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=cb)
        self._stream.start()
        return {'ok': True}

    def stop(self):
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return {'error': 'no audio'}
        audio = np.concatenate(self._chunks)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio.tobytes())
        return {'audio': base64.b64encode(buf.getvalue()).decode(), 'mimeType': 'audio/wav'}

_mic = MicAPI()

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
    js_api=_mic,
)
webview.start(
    icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
    private_mode=False,
    storage_path=STORAGE,
)
