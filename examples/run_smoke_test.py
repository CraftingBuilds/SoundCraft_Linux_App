"""Run a console-based smoke test of the SoundCraft core stack."""
from __future__ import annotations

from pathlib import Path
from pprint import pprint
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from soundcraft.core import synthesis
from soundcraft.core.ai_agent import ConsoleBridge, SoundCraftAgent, load_protocol_file
from soundcraft.core import smith_equivalence as se


class DemoBridge(ConsoleBridge):
    """Console bridge that records values for later inspection."""

    def __init__(self) -> None:
        super().__init__()
        self.collected = {}

    def note(self, msg: str) -> None:
        print(f"[Note] {msg}")

    def ask(self, var):  # type: ignore[override]
        value = super().ask(var)
        if value is not None:
            self.collected[var.name] = value
        return value

    def confirm(self, msg: str) -> bool:
        print(f"[Confirm] {msg} → yes")
        return True

    def finalize(self, values):  # type: ignore[override]
        print("[Finalize] Protocol values:")
        pprint(values)
        self.collected.update(values)


def run_protocol_demo() -> DemoBridge:
    protocol_path = Path("soundcraft/core/Agent Protocols/soundcraft_creation_protocol.yml")
    bridge = DemoBridge()
    protocol = load_protocol_file(protocol_path)
    agent = SoundCraftAgent(protocol, ui_bridge=bridge)
    agent.start()
    return bridge


def run_patch_demo() -> Path:
    patch = se.generate_patch(
        note="A4",
        duration_beats=4.0,
        bpm=72.0,
        harmonic="3/2",
        binaural_offset_hz=4.5,
        metadata={"label": "smoke-demo"},
        tempo=72,
        key_signature="A",
        instrumentation="sine_drone",
    )
    print("[Patch] Generated patch dictionary:")
    pprint(patch)

    data = synthesis.binaural_wave(
        carrier_hz=patch["frequency_hz"],
        beat_hz=patch["binaural_offset_hz"],
        duration_sec=patch["duration_seconds"],
    )
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "smoke_demo.wav"
    synthesis.write_wav(str(out_path), data)
    print(f"[Audio] Wrote demo WAV to {out_path.resolve()}")
    return out_path


def main() -> None:
    bridge = run_protocol_demo()
    print("[Bridge] Collected values:")
    pprint(bridge.collected)

    out_path = run_patch_demo()
    print(f"[Done] Smoke test completed. Output file: {out_path}")


if __name__ == "__main__":
    main()
