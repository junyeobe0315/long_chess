"""Per-ply verification log.

The format is fixed here and should not change: the trace of the final game is
part of the deliverable, and being able to diff two runs ply-by-ply is the only
practical way to debug a 17,000-move game.

Ply 0 is the starting position and carries no move, so every record's
"position before the move" is the previous record's ``fen``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import IO

FIELDS = (
    "ply",
    "fen",
    "uci",
    "critical",
    "halfmove_clock",
    "repetitions",
    "termination",
)


@dataclass(frozen=True, slots=True)
class TraceRecord:
    ply: int
    """Number of plies played, so the starting position is 0."""

    fen: str
    """Full FEN of the position *after* the move."""

    uci: str
    """The move that produced this position; empty at ply 0."""

    critical: bool
    """Whether that move was a pawn move or a capture."""

    halfmove_clock: int
    """Plies since the last pawn move or capture."""

    repetitions: int
    """How many times this position has now occurred."""

    termination: str
    """:class:`~long_chess.verifier.rules.Termination` value."""


def write_tsv(records: Iterable[TraceRecord], stream: IO[str]) -> int:
    """Write records as a TSV with a header. Returns the number written."""
    stream.write("\t".join(FIELDS) + "\n")
    count = 0
    for record in records:
        row = asdict(record)
        stream.write(
            "\t".join(
                "1" if row[f] is True else "0" if row[f] is False else str(row[f])
                for f in FIELDS
            )
            + "\n"
        )
        count += 1
    return count


def write_jsonl(records: Iterable[TraceRecord], stream: IO[str]) -> int:
    """Write records as JSON Lines. Returns the number written."""
    count = 0
    for record in records:
        stream.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")
        count += 1
    return count
