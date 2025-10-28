from __future__ import annotations

import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import yaml


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
    description: str = ""
    variables: Dict[str, Variable] = field(default_factory=dict)
    steps: List[Step] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "Option",
    "Variable",
    "Step",
    "Protocol",
    "load_protocol_file",
    "load_protocols",
    "AIAgent",
    "SoundCraftAgent",
]


_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


# ---------------------------------------------------------------------
# Protocol loading helpers
# ---------------------------------------------------------------------
def _build_options(raw_opts: Optional[Iterable[Dict[str, Any]]]) -> List[Option]:
    if not raw_opts:
        return []
    options: List[Option] = []
    for opt in raw_opts:
        if not isinstance(opt, dict):
            continue
        label = str(opt.get("label", opt.get("value", "")))
        value = opt.get("value", label)
        options.append(Option(label=label, value=value, rationale=str(opt.get("rationale", ""))))
    return options


def _build_variables(raw_vars: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, Variable]:
    variables: Dict[str, Variable] = {}
    if not raw_vars:
        return variables
    for raw in raw_vars:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        if not name:
            continue
        var = Variable(
            name=str(name),
            type=str(raw.get("type", "text")),
            prompt=str(raw.get("prompt", "")),
            required=bool(raw.get("required", True)),
            default=raw.get("default"),
            options=_build_options(raw.get("options")),
            validate_regex=raw.get("validate_regex"),
        )
        variables[var.name] = var
    return variables


def _build_steps(raw_steps: Optional[Iterable[Dict[str, Any]]]) -> List[Step]:
    steps: List[Step] = []
    if not raw_steps:
        return steps
    for raw in raw_steps:
        if not isinstance(raw, dict):
            continue
        steps.append(
            Step(
                kind=str(raw.get("kind", "")),
                ref=raw.get("ref"),
                text=str(raw.get("text", "")),
                call=raw.get("call"),
                args=dict(raw.get("args", {})) if isinstance(raw.get("args"), dict) else {},
            )
        )
    return steps


def load_protocol_file(path: str | Path) -> Protocol:
    """Load a single YAML protocol definition into a :class:`Protocol`."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    protocol_id = str(data.get("id", path.stem))
    title = str(data.get("title", protocol_id))
    version = str(data.get("version", "1.0"))
    description = str(data.get("description", ""))
    variables = _build_variables(data.get("variables"))
    steps = _build_steps(data.get("steps"))

    known_keys = {"id", "title", "version", "description", "variables", "steps"}
    metadata = {k: v for k, v in data.items() if k not in known_keys}

    return Protocol(
        id=protocol_id,
        title=title,
        version=version,
        description=description,
        variables=variables,
        steps=steps,
        metadata=metadata,
    )


def load_protocols(directory: str | Path) -> Dict[str, Protocol]:
    """Load all ``.yml``/``.yaml`` files in *directory* into Protocol objects."""
    protocols: Dict[str, Protocol] = {}
    directory = Path(directory)
    if not directory.exists():
        return protocols

    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        proto = load_protocol_file(path)
        protocols[proto.id] = proto
    return protocols


# ---------------------------------------------------------------------
# UI bridge helpers
# ---------------------------------------------------------------------
class ConsoleBridge:
    """Fallback bridge that uses defaults so automated tests do not block."""

    def ask(self, var: Variable) -> Any:
        if var.default is not None:
            print(f"[Agent] {var.name} → default {var.default}")
            return var.default

        if var.options:
            choice = var.options[0]
            print(
                "[Agent] "
                f"{var.name} has no default; selecting first option '{choice.label}' ({choice.value})."
            )
            return choice.value

        print(f"[Agent] {var.name} has no default; skipping.")
        return None

    def note(self, msg: str) -> None:
        print(msg)

    def confirm(self, msg: str) -> bool:
        print(msg)
        return True

    def finalize(self, values: Dict[str, Any]) -> None:
        print("Protocol complete:")
        for key, value in values.items():
            print(f"  {key}: {value}")


# ---------------------------------------------------------------------
# AI Agent
# ---------------------------------------------------------------------
class AIAgent:
    """Lightweight protocol runner with optional UI bridge integration."""

    def __init__(self, protocol: Protocol, ui_bridge: Optional[Any] = None):
        self.protocol = protocol
        self.ui = ui_bridge or ConsoleBridge()
        self.values: Dict[str, Any] = {}

    # -- public API -------------------------------------------------
    def start(self) -> Dict[str, Any]:
        self.values.clear()
        for idx, step in enumerate(self.protocol.steps, 1):
            self._run_step(step_idx=idx, step=step)
        return dict(self.values)

    # -- step execution --------------------------------------------
    def _run_step(self, step_idx: int, step: Step) -> None:
        kind = (step.kind or "").lower().strip()

        if kind in {"say", "note"}:
            self.ui.note(step.text)
            return

        if kind == "ask":
            if not step.ref:
                raise ValueError(f"[Protocol] Step {step_idx} missing 'ref' for ask.")
            if step.ref not in self.protocol.variables:
                raise KeyError(f"[Protocol] Variable '{step.ref}' not defined.")
            var = self.protocol.variables[step.ref]
            value = self.ui.ask(var)
            if value in (None, ""):
                value = var.default
            if value in (None, "") and var.required:
                raise ValueError(f"[Protocol] Variable '{var.name}' requires a value.")
            if value not in (None, ""):
                self.values[var.name] = value
            return

        if kind == "confirm":
            message = step.text or "Confirm?"
            result = self.ui.confirm(message)
            key = step.ref or f"confirm_{step_idx}"
            self.values[key] = result
            return

        if kind == "call":
            if not step.call:
                raise ValueError(f"[Protocol] Step {step_idx} has kind='call' but no 'call'.")
            args = self._resolve_args(step.args or {})
            result = self._execute_call(step_idx, step.call, args)
            if step.ref:
                self.values[step.ref] = result
            return

        if kind == "finalize":
            self.ui.finalize(dict(self.values))
            return

        raise ValueError(f"[Protocol] Step {step_idx} has unknown kind='{step.kind}'.")

    # -- helpers ---------------------------------------------------
    def _resolve_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        def resolve(value: Any) -> Any:
            if isinstance(value, str):
                return _VAR_PATTERN.sub(lambda m: str(self.values.get(m.group(1), "")), value)
            if isinstance(value, dict):
                return {k: resolve(v) for k, v in value.items()}
            if isinstance(value, list):
                return [resolve(item) for item in value]
            return value

        return {key: resolve(val) for key, val in args.items()}

    def _execute_call(self, step_idx: int, call_path: str, args: Dict[str, Any]) -> Any:
        """
        call_path format: 'soundcraft.core.module.function'
        """
        try:
            mod_path, func_name = call_path.rsplit(".", 1)
        except ValueError as exc:
            raise ValueError(
                f"[Protocol] Step {step_idx}: invalid call target '{call_path}'. "
                f"Expected 'package.module.function'."
            ) from exc

        try:
            mod = importlib.import_module(mod_path)
        except Exception as exc:
            raise ImportError(
                f"[Protocol] Step {step_idx}: failed to import module '{mod_path}': {exc}"
            ) from exc

        if not hasattr(mod, func_name):
            raise AttributeError(
                f"[Protocol] Step {step_idx}: module '{mod_path}' has no attribute '{func_name}'."
            )

        fn: Callable[..., Any] = getattr(mod, func_name)
        if not callable(fn):
            raise TypeError(
                f"[Protocol] Step {step_idx}: '{func_name}' in '{mod_path}' is not callable."
            )

        try:
            return fn(**args)
        except TypeError as exc:
            raise TypeError(
                f"[Protocol] Step {step_idx}: bad arguments for '{call_path}': {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"[Protocol] Step {step_idx}: error in '{call_path}': {exc}"
            ) from exc


class SoundCraftAgent(AIAgent):
    """Semantic alias for the DAW to use."""

    def __init__(self, protocol: Protocol, ui_bridge: Optional[Any] = None):
        super().__init__(protocol=protocol, ui_bridge=ui_bridge)
