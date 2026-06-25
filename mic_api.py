"""Native microphone capture with automatic silence detection.

Exposes start() / poll() / stop() to the pywebview JS bridge.
- start(): begin recording
- poll(): returns {'recording': True} while still capturing, or the final
  {'audio': <b64 wav>, 'mimeType': 'audio/wav'} once the speaker goes quiet.
- stop(): force-finish immediately (used when the user taps to stop).

IMPORTANT: PortAudio does not allow stopping/closing a stream from inside its
own audio callback. The callback only sets flags; the stream is torn down from
poll()/stop()/start(), which run on the main (bridge) thread.
"""
import base64, io, wave, threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500      # RMS below this counts as silence (int16 scale)
SILENCE_HANG = 0.7           # seconds of silence after speech -> auto-stop
MAX_SECONDS = 10             # hard cap
MIN_SPEECH = 0.20            # need at least this much loud audio to count as real


class MicAPI:
    def __init__(self):
        self._lock = threading.Lock()
        self._reset()

    def _reset(self):
        self._stream = None
        self._chunks = []
        self._recording = False
        self._heard_speech = False
        self._silence_run = 0.0
        self._speech_run = 0.0
        self._total = 0.0
        self._should_finish = False  # set by callback, acted on by poll/stop

    def start(self):
        # Tear down any leftover stream from a previous run first.
        self._teardown_stream()
        with self._lock:
            self._chunks = []
            self._recording = True
            self._heard_speech = False
            self._silence_run = 0.0
            self._speech_run = 0.0
            self._total = 0.0
            self._should_finish = False

        def cb(indata, frames, time_info, status):
            with self._lock:
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
                # Flag (do NOT stop the stream here) when done speaking or capped.
                if (self._heard_speech and self._silence_run >= SILENCE_HANG) or self._total >= MAX_SECONDS:
                    self._recording = False
                    self._should_finish = True

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype='int16',
            blocksize=int(SAMPLE_RATE * 0.05), callback=cb,
        )
        self._stream.start()
        return {'ok': True}

    def _teardown_stream(self):
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    def _build_result(self):
        with self._lock:
            chunks = self._chunks
            self._chunks = []
        if not chunks:
            return {'error': 'no audio'}
        audio = np.concatenate(chunks)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return {'audio': base64.b64encode(buf.getvalue()).decode(), 'mimeType': 'audio/wav'}

    def poll(self):
        # Auto-finished by silence detection?
        if self._should_finish:
            self._should_finish = False
            self._teardown_stream()
            return self._build_result()
        if self._recording:
            return {'recording': True}
        # Not recording and nothing flagged -> nothing to do
        return {'recording': False, 'error': 'no audio'}

    def stop(self):
        with self._lock:
            self._recording = False
            self._should_finish = False
        self._teardown_stream()
        return self._build_result()
