#!/usr/bin/env python3
"""Does the cheap capacity estimate hold up against the packer?

    uv run python scripts/capacity_study.py data/skeleton.json

Measures every segment's start position two ways — actually packing it, and
guessing — and reports whether the guess is ever *pessimistic*, which is the
direction that would make a rescheduling search discard valid skeletons
without noticing.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import chess

from long_chess.filler import (
    estimate_capacity,
    features,
    measure_capacity,
    measure_segment_capacity,
    segment_target,
)
from long_chess.skeleton import load, potential

# Deliberately awkward positions, to see where capacity actually runs out.
PROBES = {
    "bare kings": "7k/8/8/8/8/8/8/K7 w - - 0 1",
    "king + rook vs king": "7k/8/8/8/8/8/R7/K7 w - - 0 1",
    "king + knight vs king": "7k/8/8/8/8/8/8/KN6 w - - 0 1",
    "only White can move": "7k/5ppp/8/8/8/8/8/K6R w - - 0 1",
    "opening": chess.STARTING_FEN,
    "locked pawns": "7k/8/8/p1p1p1p1/P1P1P1P1/8/8/K7 w - - 0 1",
}


def study(board: chess.Board, seed: int) -> dict:
    rng = random.Random(seed)
    measured = measure_capacity(board, rng)
    estimated = estimate_capacity(board, random.Random(seed))
    stats = features(board)
    pieces, pawn_steps = potential(board)
    return {
        "fen": board.fen(),
        "pieces": pieces,
        "pawn_steps": pawn_steps,
        "measured": measured,
        "estimated": estimated,
        "quiet_moves": stats.quiet_moves,
        "reversible_movers": stats.white_movers + stats.black_movers,
        "free_pieces": stats.free_pieces,
        "blocked_by": stats.blocked_by,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="capacity_study")
    parser.add_argument("skeleton", type=Path)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("-o", "--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    skeleton = load(args.skeleton)

    rows = []
    for index, segment in enumerate(skeleton.segments):
        row = study(segment.board_at_start(), args.seed + index)
        row["segment"] = index
        row["in_segment"] = measure_segment_capacity(
            segment, random.Random(args.seed + index)
        )
        row["segment_target"] = segment_target(segment)
        rows.append(row)

    print("segments whose start position holds nothing on its own:")
    blocked = [row for row in rows if row["measured"] == 0]
    for row in blocked:
        print(
            f"  seg {row['segment']:>3}  {row['blocked_by']}"
            f"  -> in-segment capacity {row['in_segment']}"
            f"/{row['segment_target']}"
        )

    full = [row for row in rows if row["in_segment"] >= row["segment_target"]]
    print()
    print(f"segments packing to their target : {len(full)}/{len(rows)}")
    partial = [row for row in rows if 0 < row["in_segment"] < row["segment_target"]]
    print(
        f"segments landing part-way        : {len(partial)}  "
        "(capacity is close to binary)"
    )

    pessimistic = [row for row in rows if row["estimated"] < row["measured"]]
    print(f"estimates below the measured value: {len(pessimistic)}  (must be 0)")
    for row in pessimistic[:5]:
        print(f"  segment {row['segment']}: est {row['estimated']} < {row['measured']}")

    print()
    print("probe positions")
    header = f"{'position':>22} {'pieces':>7} {'capacity':>9} {'estimate':>9}"
    print(header + f" {'blocked by':>34}")
    probes = []
    for name, fen in PROBES.items():
        row = study(chess.Board(fen), args.seed)
        row["name"] = name
        probes.append(row)
        print(
            f"{name:>22} {row['pieces']:>7} {row['measured']:>9} "
            f"{row['estimated']:>9} {str(row['blocked_by']):>34}"
        )

    bad = [row for row in probes if row["estimated"] < row["measured"]]
    if bad:
        print(f"\nFAIL: {len(bad)} probe estimate(s) pessimistic", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"segments": rows, "probes": probes}, indent=2), encoding="utf-8"
        )
        print(f"\nwrote {args.output}")

    return 1 if pessimistic else 0


if __name__ == "__main__":
    sys.exit(main())
