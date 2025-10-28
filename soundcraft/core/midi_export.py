"""
Minimal MIDI export using mido.
"""
import mido

def write_note_sequence(wav_title: str, notes: list[tuple[int,int,int]], out_mid: str, tempo_bpm: int = 120):
    """
    notes: list of (note_number, velocity, length_ticks)
    """
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)

    tempo = mido.bpm2tempo(tempo_bpm)
    track.append(mido.MetaMessage('set_tempo', tempo=tempo))

    for n, vel, length in notes:
        track.append(mido.Message('note_on', note=n, velocity=vel, time=0))
        track.append(mido.Message('note_off', note=n, velocity=0, time=length))

    mid.save(out_mid)
    return out_mid
