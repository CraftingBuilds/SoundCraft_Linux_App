\
"""
Smith Equivalence Formula + helpers (v6.1 compatible placeholders).

This module provides:
- base reference A4 = 432 or 440 configurable
- mapping cosmic/cycle rates to audible Hz via octave scaling
- note <-> frequency helpers
- slots to drop-in Smith Equivalence App v6.1 data tables later
"""

from __future__ import annotations
import math
from dataclasses import dataclass

A4 = 432.0  # You can switch to 440.0 if desired

# Equal temperament helpers
def note_to_freq(note_number: int, a4: float = A4) -> float:
    # MIDI note 69 is A4
    return a4 * (2 ** ((note_number - 69) / 12))

def freq_to_note_num(freq: float, a4: float = A4) -> float:
    return 69 + 12 * math.log2(freq / a4)

@dataclass
class SmithMap:
    base_ref: float = A4
    min_audible: float = 16.35   # C0
    max_audible: float = 20000.0

    def cycle_to_hz(self, cycle_rate: float) -> float:
        """
        Map a cosmic/ritual cycle rate (per unit time) into audible range by octave translation.
        Example: daily cycle -> normalize -> shift to audible band.
        """
        if cycle_rate <= 0:
            raise ValueError("cycle_rate must be positive")
        hz = cycle_rate
        while hz < self.min_audible:
            hz *= 2.0
        while hz > self.max_audible:
            hz /= 2.0
        return hz

    def to_nearest_note(self, hz: float) -> tuple[int, float]:
        n = round(freq_to_note_num(hz, self.base_ref))
        return n, note_to_freq(n, self.base_ref)
