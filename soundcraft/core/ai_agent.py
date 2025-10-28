# soundcraft/core/ai_agent.py
from __future__ import annotations
import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional


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
    steps: List[Step] = field(default_factory=list)


# ---------------------------------------------------------------------
# AI Agent
# ---------------------------------------------------------------------
class AIAgent:
    """
    Minimal protocol runner. Each step may:
      - kind == 'say'      -> print/display text
      - kind == 'call'     -> dynamic import+call "pkg.mod.func"
    """

    def __init__(self, protocol: Protocol):
        self.protocol = protocol

    def start(self) -> None:
        for idx, step in enumerate(self.protocol.steps, 1):
            self._run_step(step_idx=idx, step=step)

    def _run_step(self, step_idx: int, step: Step) -> None:
        kind = (step.kind or "").lower().strip()
        if kind == "say":
            # In your Qt app, you probably route this to the log/console UI.
            print(step.text)
            return

        if kind == "call":
            if not step.call:
                raise ValueError(f"[Protocol] Step {step_idx} has kind='call' but no 'call' target.")
            self._execute_call(step_idx, step.call, step.args or {})
            return

        # Unknown step kinds produce a clear error
        raise ValueError(f"[Protocol] Step {step_idx} has unknown kind='{step.kind}'.")

    def _execute_call(self, step_idx: int, call_path: str, args: Dict[str, Any]) -> Any:
        """
        call_path format: 'soundcraft.core.module.function'
        """
        try:
            mod_path, func_name = call_path.rsplit(".", 1)
        except ValueError:
            raise ValueError(
                f"[Protocol] Step {step_idx}: invalid call target '{call_path}'. "
                f"Expected 'package.module.function'."
            )

        try:
            mod = importlib.import_module(mod_path)
        except Exception as e:
            raise ImportError(
                f"[Protocol] Step {step_idx}: failed to import module '{mod_path}': {e}"
            ) from e

        if not hasattr(mod, func_name):
            raise AttributeError(
                f"[Protocol] Step {step_idx}: module '{mod_path}' "
                f"has no attribute '{func_name}'."
            )

        fn: Callable[..., Any] = getattr(mod, func_name)
        if not callable(fn):
            raise TypeError(
                f"[Protocol] Step {step_idx}: '{func_name}' in '{mod_path}' is not callable."
            )

        try:
            return fn(**args)
        except TypeError as e:
            # Better message when arguments don't match
            raise TypeError(
                f"[Protocol] Step {step_idx}: bad arguments for '{call_path}': {e}"
            ) from e
        except Exception as e:
            # Surface the original error, but keep protocol context
            raise RuntimeError(
                f"[Protocol] Step {step_idx}: error in '{call_path}': {e}"
            ) from e
