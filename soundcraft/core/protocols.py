\
"""
Protocols format + loader (YAML). Defines ritual steps and default parameters.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import yaml

@dataclass
class Protocol:
    name: str
    steps: list[dict[str, Any]] = field(default_factory=list)

def load_protocol(path: str) -> Protocol:
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    return Protocol(name=data.get("name","Unnamed Protocol"), steps=data.get("steps", []))
