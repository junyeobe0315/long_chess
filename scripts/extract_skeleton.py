#!/usr/bin/env python3
"""Strip the filler out of a padded game and report the skeleton.

    uv run python scripts/extract_skeleton.py data/longest.pgn -o data/skeleton.json

Cross-checks against Tom 7's hand-built skeleton when it is available, since
agreeing with an independently produced artefact is worth more than agreeing
with ourselves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from long_chess.skeleton import (
    analyse,
    compress,
    dump,
    find_cross_segment_repeats,
    split_game,
    to_pgn,
)
from long_chess.verifier import moves_from_pgn, moves_from_san, verify_game

DATA = Path(__file__).parent.parent / "data"
REFERENCE_SKELETON = DATA / "skeleton_reference.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="extract_skeleton")
    parser.add_argument("pgn", type=Path, help="padded game to compress")
    parser.add_argument("-o", "--output", type=Path, help="write skeleton JSON here")
    parser.add_argument("--pgn-out", type=Path, help="also write the skeleton as PGN")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    full = split_game(moves_from_pgn(args.pgn))
    print(f"input       {full.plies} ply, {full.critical_count} segments")

    repeats = find_cross_segment_repeats(full)
    if repeats:
        print(
            f"FAIL: {len(repeats)} position(s) recur across segments; "
            "segment independence does not hold",
            file=sys.stderr,
        )
        for first, second, fen in repeats[:5]:
            print(f"  segments {first} and {second}: {fen}", file=sys.stderr)
        return 1
    print("independence  no position recurs across segments")

    skeleton = compress(full)
    print(f"skeleton    {skeleton.plies} ply, {skeleton.critical_count} segments")

    if skeleton.critical_sans() != full.critical_sans():
        print("FAIL: compression changed the critical sequence", file=sys.stderr)
        return 1
    if skeleton.actors != full.actors:
        print("FAIL: compression changed a critical actor", file=sys.stderr)
        return 1
    print("preserved     critical moves, their order and their actors")

    result = verify_game(list(skeleton.moves))
    print(
        f"verified      {result.plies} ply, {result.termination.value}, "
        f"{result.critical_count} critical segments"
    )
    if result.plies != skeleton.plies:
        print("FAIL: the skeleton terminates early", file=sys.stderr)
        return 1

    if REFERENCE_SKELETON.exists():
        reference = split_game(
            moves_from_san(REFERENCE_SKELETON.read_text(encoding="utf-8"))
        )
        identical = skeleton.moves == reference.moves
        print(
            f"vs tom7       {reference.plies} ply, "
            f"{'identical move for move' if identical else 'DIFFERS'}"
        )
        if not identical:
            return 1

    print()
    print(analyse(skeleton).format_report())

    if args.output:
        dump(skeleton, args.output)
        print(f"\nwrote {args.output}")
    if args.pgn_out:
        args.pgn_out.parent.mkdir(parents=True, exist_ok=True)
        args.pgn_out.write_text(
            to_pgn(skeleton, Event="Critical skeleton", Site="skeleton"),
            encoding="utf-8",
        )
        print(f"wrote {args.pgn_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
