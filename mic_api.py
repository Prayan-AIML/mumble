"""Native microphone capture with automatic silence detection.

Exposes start() / poll() / stop() to the pywebview JS bridge.
- start(): begin recording
- poll(): returns {'recording': True} while still capturing, or the final
  {'audio': <b64 wav>, 'mimeType': 'audio/wav'} once the speaker goes quiet.
- stop(): force-finish immediately (used when the user taps to stop).
"""
import base64, io, wave
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500      # RMS below this counts as silence (int16 scale)
SILENCE_HANG = 0.7           # seconds of silence after speech -> auto-stop
MAX_SECONDS = 10             # hard cap
MIN_SPEECH = 0.25            # need at least this much loud audio to count as real


class MicAPI:
    def __init__(self):
        self._stream = None
        self._chunks = []
        self._recording = False
        self._heard_speech = False
        self._silence_run = 0.0
        self._speech_run = 0.0
        self._total = 0.0
        self._done = None

    def start(self):
        self._chunks = []
        self._recording = True
        self._heard_speech = False
        self._silence_run = 0.0
        self._speech_run = 0.0
        self._total = 0.0
        self._done = None

        def cb(indata, frames, t, status):
            if not self._recording:
                return
            self._chunks.append(indata.copy())
            dur = frames / SAMPLE_RATE
            self._total += dur
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            if rms >= SILENCE_THRESHOLD:
                self._speech_run += dur
                self._silence_run = 0.0
                if self._speech_run >= MIN_SPEECH:
                    self._heard_speech = True
            else:
                self._silence_run += dur
            # auto-finish: spoke then went quiet, or hit the hard cap
            if (self._heard_speech and self._silence_run >= SILENCE_HANG) or self._total >= MAX_SECONDS:
                self._finish()

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype='int16',
            blocksize=int(SAMPLE_RATE * 0.05), callback=cb,
        )
        self._stream.start()
        return {'ok': True}

    def _finish(self):
        if not self._recording:
            return
        self._recording = False
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
        self._stream = None
        if not self._chunks:
            self._done = {'error': 'no audio'}
            return
        audio = np.concatenate(self._chunks)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        self._done = {'audio': base64.b64encode(buf.getvalue()).decode(), 'mimeType': 'audio/wav'}

    def poll(self):
        if self._done is not None:
            return self._done
        return {'recording': True}

    def stop(self):
        self._finish()
        return self._done or {'error': 'no audio'}
