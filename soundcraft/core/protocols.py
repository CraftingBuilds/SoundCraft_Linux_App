"""Utilities for loading protocol definitions."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from .ai_agent import Protocol, load_protocol_file


def load_protocol(path: str | Path) -> Protocol:
    """Load a single protocol YAML file."""
    return load_protocol_file(path)


def load_protocols(directory: str | Path) -> Dict[str, Protocol]:
    """Convenience proxy to :func:`soundcraft.core.ai_agent.load_protocols`."""
    from .ai_agent import load_protocols as _load_all

    return _load_all(directory)


__all__ = ["Protocol", "load_protocol", "load_protocols"]
