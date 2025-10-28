"""
Voice recorder to WAV using sounddevice + soundfile.
"""
import sounddevice as sd
import soundfile as sf

def record_wav(path: str, duration_sec: float, samplerate: int = 48000, channels: int = 1):
    print(f"[Recorder] Recording {duration_sec}s → {path}")
    audio = sd.rec(int(duration_sec * samplerate), samplerate=samplerate, channels=channels, dtype='float32')
    sd.wait()
    sf.write(path, audio, samplerate)
    return path
