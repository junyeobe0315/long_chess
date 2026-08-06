"""Skeleton serialisation.

The packer, the batch generator and the scheduling analysis all pass
skeletons around, and rescheduling swaps individual segments
in and out, so segments are stored as independent records carrying their own
start position rather than as one flat move list.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chess

from .segment import Segment, Skeleton

FORMAT_VERSION = 1


def to_dict(skeleton: Skeleton) -> dict[str, Any]:
    return {
        "version": FORMAT_VERSION,
        "ends_in_checkmate": skeleton.ends_in_checkmate,
        "segments": [
            {
                "start_fen": segment.start_fen,
                "bridge": [move.uci() for move in segment.bridge_moves],
                "critical": segment.critical_move.uci(),
            }
            for segment in skeleton.segments
        ],
    }


def from_dict(data: dict[str, Any]) -> Skeleton:
    version = data.get("version")
    if version != FORMAT_VERSION:
        raise ValueError(f"unsupported skeleton format version {version!r}")
    return Skeleton(
        tuple(
            Segment(
                start_fen=record["start_fen"],
                bridge_moves=tuple(
                    chess.Move.from_uci(uci) for uci in record["bridge"]
                ),
                critical_move=chess.Move.from_uci(record["critical"]),
            )
            for record in data["segments"]
        ),
        ends_in_checkmate=data["ends_in_checkmate"],
    )


def dump(skeleton: Skeleton, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(skeleton), indent=2), encoding="utf-8")


def load(path: str | Path) -> Skeleton:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def to_pgn(skeleton: Skeleton, **headers: str) -> str:
    """Render the skeleton as a PGN, so it can be eyeballed in a board viewer."""
    board = chess.Board(skeleton.start_fen)
    game = chess.pgn.Game()
    game.setup(board)
    for key, value in headers.items():
        game.headers[key] = value
    node: Any = game
    for move in skeleton.moves:
        node = node.add_variation(move)
    return str(game)
