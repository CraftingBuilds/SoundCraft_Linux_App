from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import math

__all__ = [
    "note_to_frequency",
    "compute_frequency",
    "generate_patch",
]


# Basic A4=440 equal-temperament map helper ------------------------------
_NOTE_INDEX = {
    # Support common sharps & flats up to simple studio ranges
    "C":  -9, "C#": -8, "Db": -8,
    "D":  -7, "D#": -6, "Eb": -6,
    "E":  -5,
    "F":  -4, "F#": -3, "Gb": -3,
    "G":  -2, "G#": -1, "Ab": -1,
    "A":   0, "A#":  1, "Bb":  1,
    "B":   2,
}

def note_to_frequency(note: str, a4_hz: float = 440.0) -> float:
    """
    Convert note name like 'A4', 'C#3', 'Bb2' to frequency in Hz using A4=a4_hz.
    Falls back to A4 if parsing fails.
    """
    if not note:
        return a4_hz

    note = note.strip()
    # Parse pitch class + octave
    # Accept forms like C4, C#4, Db4
    pitch = None
    octave = None

    # Find the boundary between letters/#/b and the octave digits
    for i in range(len(note)):
        if note[i].isdigit() or (note[i] in "+-" and i > 0):
            pitch = note[:i]
            octave = note[i:]
            break
    if pitch is None:
        # No digits – try to treat as pitch class only (assume octave 4)
        pitch, octave = note, "4"

    pitch = pitch.strip()
    try:
        octave_val = int(octave)
    except Exception:
        octave_val = 4

    if pitch not in _NOTE_INDEX:
        # Best-effort uppercase normalize
        pitch = pitch.capitalize()
    if pitch not in _NOTE_INDEX:
        return a4_hz

    # Semitone distance from A4
    n = _NOTE_INDEX[pitch] + 12 * (octave_val - 4)
    return a4_hz * (2.0 ** (n / 12.0))


# Smith Equivalence placeholder ------------------------------------------
def compute_frequency(
    base: Optional[float] = None,
    note: Optional[str] = None,
    a4_hz: float = 440.0,
    ratio_num: int = 1,
    ratio_den: int = 1,
) -> float:
    """
    Compute a frequency using either a raw base or a note name,
    optionally scaled by a rational ratio (harmonic).
    """
    if base is None:
        base = note_to_frequency(note or "A4", a4_hz=a4_hz)

    if ratio_den == 0:
        ratio_den = 1
    return float(base) * (ratio_num / ratio_den)


# Patch generator used by the protocol -----------------------------------
def generate_patch(
    note: Optional[str] = None,
    base_hz: Optional[float] = None,
    a4_hz: float = 440.0,
    harmonic: Optional[str] = None,
    binaural_offset_hz: float = 0.0,
    duration_beats: float = 4.0,
    bpm: float = 120.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a simple synthesis 'patch' dict that your synthesis layer can consume.

    Args:
        note: Optional note like 'C4', 'A4', etc.
        base_hz: If provided, overrides note.
        a4_hz: Concert pitch reference.
        harmonic: optional 'p/q' string (e.g., '3/2') applied to base.
        binaural_offset_hz: add a second channel with base+offset if nonzero.
        duration_beats: musical length in beats.
        bpm: tempo used to convert beats -> seconds.
        metadata: free-form info to carry forward.

    Returns:
        Dict with fields safe for downstream synthesis/MIDI/WAV export.
    """
    # Resolve base frequency
    if base_hz is not None:
        f0 = float(base_hz)
    else:
        f0 = note_to_frequency(note or "A4", a4_hz=a4_hz)

    # Apply harmonic ratio if requested
    ratio_num, ratio_den = 1, 1
    if harmonic:
        try:
            parts = harmonic.replace(" ", "").split("/")
            if len(parts) == 2:
                ratio_num = int(parts[0])
                ratio_den = int(parts[1]) if int(parts[1]) != 0 else 1
        except Exception:
            ratio_num, ratio_den = 1, 1
    f_main = compute_frequency(base=f0, ratio_num=ratio_num, ratio_den=ratio_den, a4_hz=a4_hz)

    # Convert beats to seconds
    seconds = (duration_beats / max(bpm, 1e-6)) * 60.0

    patch = {
        "patch_id": f"patch_{abs(hash((note, base_hz, harmonic, binaural_offset_hz, duration_beats, bpm)))% (10**10)}",
        "note": note,
        "a4_hz": a4_hz,
        "base_hz": f0,
        "frequency_hz": f_main,
        "binaural_offset_hz": float(binaural_offset_hz),
        "duration_beats": float(duration_beats),
        "bpm": float(bpm),
        "duration_seconds": seconds,
        "voices": [
            {"kind": "sine", "hz": f_main, "gain": 0.9}
        ],
        "metadata": metadata or {},
    }

    # If binaural is requested, add a second voice
    if abs(binaural_offset_hz) > 1e-9:
        patch["voices"].append({"kind": "sine", "hz": f_main + float(binaural_offset_hz), "gain": 0.9})

    return patch
