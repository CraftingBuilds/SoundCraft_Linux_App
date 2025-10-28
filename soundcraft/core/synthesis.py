\
"""
Basic synthesis: sine tones and binaural beat writer.
"""
from __future__ import annotations
import numpy as np
import soundfile as sf

def sine_wave(freq: float, duration_sec: float, samplerate: int = 48000, amplitude: float = 0.2):
    t = np.linspace(0, duration_sec, int(samplerate * duration_sec), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)

def binaural_wave(carrier_hz: float, beat_hz: float, duration_sec: float, samplerate: int = 48000, amplitude: float = 0.2):
    left = sine_wave(carrier_hz - beat_hz/2.0, duration_sec, samplerate, amplitude)
    right = sine_wave(carrier_hz + beat_hz/2.0, duration_sec, samplerate, amplitude)
    return np.stack([left, right], axis=1)

def write_wav(path: str, data, samplerate: int = 48000):
    sf.write(path, data, samplerate)
    return path
