"""The abstract model of critical-event scheduling.

The CP-SAT half needs the optional ``solver`` extra: uv sync --extra solver.
The problem statement (:mod:`.shape`) and the solver-free cross-check
(:mod:`.independent`) do not — and because a submodule import always runs this
``__init__``, the solver-backed names below are loaded lazily, on first
access. ``from long_chess.model import Shape, analyse_independently`` works on
a solver-less install; ``from long_chess.model import solve`` fails only when
actually asked for.
"""

from .independent import IndependentResult
from .independent import analyse as analyse_independently
from .shape import (
    CHECKMATE,
    DRAW,
    ENDINGS,
    Shape,
    all_shapes,
    require_ending,
)

_SOLVER_EXPORTS = {
    "Handles": "abstract",
    "Inconclusive": "abstract",
    "Solution": "abstract",
    "build": "abstract",
    "solve": "abstract",
    "Observation": "validate",
    "ValidationResult": "validate",
    "observe": "validate",
    "validate": "validate",
}

__all__ = [
    "CHECKMATE",
    "DRAW",
    "ENDINGS",
    "Handles",
    "Inconclusive",
    "IndependentResult",
    "Observation",
    "Shape",
    "Solution",
    "ValidationResult",
    "all_shapes",
    "analyse_independently",
    "build",
    "observe",
    "require_ending",
    "solve",
    "validate",
]


def __getattr__(name: str):
    """PEP 562: import the ortools-backed half only when it is asked for."""
    submodule = _SOLVER_EXPORTS.get(name)
    if submodule is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(f".{submodule}", __name__), name)
    # Cache the resolved object. For `validate` this deliberately shadows the
    # submodule of the same name with the function, exactly as the old eager
    # import did.
    globals()[name] = value
    return value
