#!/usr/bin/env python3
import os, sys, base64, io, wave, platform, pathlib
import numpy as np
import sounddevice as sd
import webview

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
