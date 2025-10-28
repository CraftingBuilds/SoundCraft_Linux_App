# SoundCraft (v1) – Linux Edition

**Purpose:** Ritual-grade audio engine with built-in DAW GUI, Smith Equivalence,
voice recorder, TTS, and an AI ritual assistant that follows protocol files to
help you export MIDI and WAV.

## Features in this scaffold
- PyQt6 GUI shell with a simple DAW layout (Transport, Track List, Timeline)
- Smith Equivalence core (baseline mapping + helpers)
- Synthesis (sine + binaural beat writer) → WAV
- Voice recorder (mic → WAV) using `sounddevice`/`soundfile`
- TTS (offline) using `pyttsx3` → WAV
- MIDI export using `mido`
- Protocol-driven ritual agent (rule-based placeholder) with hook for LLM
- Starseed theme accents: Blue `#1F3B76`, Gold `#D8C48A`

> LightCraft is **not** included (separate project by design).

## Quickstart

```bash
# 1) Create venv (Python 3.12 recommended)
python3 -m venv .venv
source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run GUI
python -m soundcraft.ui.qt.main
```

## Notes
- If `sounddevice` complains about backends, install PortAudio dev packages:
  - Debian/Ubuntu: `sudo apt-get install libportaudio2 portaudio19-dev`
- For MIDI out via ALSA/RTMIDI, you may need: `sudo apt-get install libasound2-dev`

## Project Structure
```
soundcraft/
  core/
    smith_equivalence.py
    synthesis.py
    recorder.py
    tts_engine.py
    midi_export.py
    wav_export.py
    protocols.py
    ai_agent.py
  ui/qt/
    main.py
    daw.py
    theme.py
data/
  presets/
  protocols/
```
