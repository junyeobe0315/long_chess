"""Independent FIDE game verifier.

This package must not import from anywhere else in ``long_chess``. If the
search ever needs something in here, move the shared part *out* rather than
letting the verifier depend on the code it is meant to check.
"""

from .game import (
    GameAlreadyOver,
    GameResult,
    GameVerifier,
    IllegalMove,
    VerificationError,
    verify_game,
)
from .pgn import moves_from_pgn, moves_from_san, moves_from_uci
from .rules import (
    FIVEFOLD_REPETITION_COUNT,
    SEVENTYFIVE_MOVE_PLY_LIMIT,
    RepetitionKey,
    Termination,
    classify_position,
    is_critical,
    repetition_key,
)
from .trace import TraceRecord, write_jsonl, write_tsv

__all__ = [
    "FIVEFOLD_REPETITION_COUNT",
    "SEVENTYFIVE_MOVE_PLY_LIMIT",
    "GameAlreadyOver",
    "GameResult",
    "GameVerifier",
    "IllegalMove",
    "RepetitionKey",
    "Termination",
    "TraceRecord",
    "VerificationError",
    "classify_position",
    "is_critical",
    "moves_from_pgn",
    "moves_from_san",
    "moves_from_uci",
    "repetition_key",
    "verify_game",
    "write_jsonl",
    "write_tsv",
]
