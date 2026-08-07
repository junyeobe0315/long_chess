#!/usr/bin/env python3
"""Dump every legal move at every position of a game, for the C differential.

    uv run python scripts/dump_legal_moves.py data/longest.pgn -o /tmp/py.moves

The companion is `checker/longest_check.c --dump-moves`, and the two outputs
are meant to be compared with `cmp`. Replaying the same moves only shows that
two move generators agree about the moves that were *played*; the ones that
were not are where a generator's disagreements live — a castling right one
side kept, an en passant capture one side offers, a pin one side honours.
Dumping the whole legal-move set at every position asks about all of them.

One line per ply, starting at ply 0 (the initial array) and ending at the
position after the last move played:

    <ply>\\t<space-separated UCI moves, sorted>

The sort is plain ascending byte order, which `sorted()` on ASCII UCI strings
and `strcmp` in C agree on.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chess

from long_chess.verifier import moves_from_pgn


def dump_lines(moves: list[chess.Move]) -> list[str]:
    """Yield one `<ply>\\t<moves>` line per position, ply 0 first.

    The moves are pushed without checking them: `moves_from_pgn` has already
    read them off a board, and judging the game is
    `long_chess.verifier.verify_game`'s job, not this script's.
    """
    board = chess.Board()
    lines = []
    for ply in range(len(moves) + 1):
        legal = sorted(move.uci() for move in board.legal_moves)
        lines.append(f"{ply}\t{' '.join(legal)}")
        if ply < len(moves):
            board.push(moves[ply])
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dump_legal_moves")
    parser.add_argument("pgn", type=Path, help="game to walk")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="write the per-ply legal-move dump here",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        moves = moves_from_pgn(args.pgn)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    lines = dump_lines(moves)
    total = sum(len(line.split("\t")[1].split()) for line in lines)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"positions     {len(lines)}  (ply 0 .. {len(moves)})")
    print(f"legal moves   {total}  ({total / len(lines):.1f} per position)")
    print(f"written       {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
