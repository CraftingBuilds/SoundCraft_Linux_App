# soundcraft/core/ai_agent.py
from __future__ import annotations
import os, yaml, re, importlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional
# from .smith_equivalence import compute_frequency  # example existing call
# from .midi_export import export_midi
# from .wav_export import export_wav

# ---------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------
@dataclass
class Option:
    label: str
    value: Any
    rationale: str = ""

@dataclass
class Variable:
    name: str
    type: str = "text"
    prompt: str = ""
    required: bool = True
    default: Any = None
    options: List[Option] = field(default_factory=list)
    validate_regex: Optional[str] = None

@dataclass
class Step:
    kind: str
    ref: Optional[str] = None
    text: str = ""
    call: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Protocol:
    id: str
    title: str
    version: str
    variables: List[Variable]
    steps: List[Step]

# ---------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------
def load_protocols(base_dir: str) -> Dict[str, Protocol]:
    protocols = {}
    for fname in os.listdir(base_dir):
        if not fname.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(base_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        variables = [
            Variable(
                name=v["name"],
                type=v.get("type", "text"),
                prompt=v.get("prompt", ""),
                required=v.get("required", True),
                default=v.get("default"),
                options=[Option(**o) for o in v.get("options", [])],
                validate_regex=v.get("validate_regex")
            )
            for v in data.get("variables", [])
        ]
        steps = [Step(**s) for s in data.get("steps", [])]
        p = Protocol(
            id=data["id"],
            title=data.get("title", data["id"]),
            version=data.get("version", "1.0"),
            variables=variables,
            steps=steps
        )
        p.source_path = path  # track file path for persistence
        protocols[p.id] = p
    return protocols

# ---------------------------------------------------------------------
# Runtime engine
# ---------------------------------------------------------------------
class SoundCraftAgent:
    def __init__(self, protocol: Protocol, ui_bridge):
        """
        ui_bridge: object with .ask(var), .note(msg), .confirm(msg), .finalize(values)
        """
        self.p = protocol
        self.ctx: Dict[str, Any] = {}
        self.ui = ui_bridge

    def start(self):
        self.ui.note(f"Initiating {self.p.title} v{self.p.version}")
        for step in self.p.steps:
            self._run_step(step)

    def _run_step(self, s: Step):
        if s.kind == "note":
            self.ui.note(s.text)

        elif s.kind == "ask":
            var = next(v for v in self.p.variables if v.name == s.ref)
            val = self.ui.ask(var)

            # Handle special dynamic options
            if val in ("__TEMP__", "__ADD__"):
                label, ok1 = self.ui.get_text("Label", f"Enter label for new {var.name}:")
                if not ok1:
                    return
                value, ok2 = self.ui.get_text("Value", f"Enter internal value for '{label}':")
                if not ok2:
                    return
                rationale, ok3 = self.ui.get_text(
                    "Rationale",
                    f"Why does '{label}' belong here? (short meaning)",
                )
                if not ok3:
                    return

                new_opt = {"label": label, "value": value, "rationale": rationale}

                if val == "__ADD__":
                    try:
                        proto_file = getattr(self.p, "source_path", None)
                        if proto_file:
                            append_option_to_yaml(proto_file, var.name, new_opt)
                            self.ui.note(f"Saved new option '{label}' permanently to protocol.")
                        else:
                            self.ui.note("Cannot locate YAML file path; temporary only.")
                    except Exception as e:
                        self.ui.note(f"YAML append failed: {e}")

                # For both TEMP and ADD: treat as active value
                self.ctx[var.name] = value
                return

            # Normal path
            self.ctx[var.name] = val

        elif s.kind == "confirm":
            if not self.ui.confirm(s.text):
                self.ui.note("User cancelled operation.")
                return

        elif s.kind == "call":
            self._execute_call(s.call, s.args)

        elif s.kind == "finalize":
            self.ui.finalize(self.ctx)

    def _execute_call(self, dotted: str, args: Dict[str, Any]):
        modname, funcname = dotted.rsplit(".", 1)
        mod = importlib.import_module(modname)
        fn = getattr(mod, funcname)
        resolved = {k: self._resolve(v) for k, v in args.items()}
        result = fn(**resolved)
        if isinstance(result, dict):
            self.ctx.update(result)

    def _resolve(self, val):
        if isinstance(val, str):
            for k, v in self.ctx.items():
                val = val.replace("${" + k + "}", str(v))
        return val


# ---------------------------------------------------------------------
# Persistent Protocol Update System
# ---------------------------------------------------------------------
def append_option_to_yaml(protocol_path: str, var_name: str, new_option: dict):
    """
    Adds a new option to the given variable name within a YAML protocol.
    new_option must be a dict like {'label': ..., 'value': ..., 'rationale': ...}
    """
    if not os.path.exists(protocol_path):
        raise FileNotFoundError(f"Protocol file not found: {protocol_path}")

    with open(protocol_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    updated = False
    for var in data.get("variables", []):
        if var.get("name") == var_name:
            opts = var.setdefault("options", [])
            opts.append(new_option)
            updated = True
            break

    if updated:
        with open(protocol_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    else:
        raise KeyError(f"Variable '{var_name}' not found in {protocol_path}")
