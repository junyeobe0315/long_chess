#!/usr/bin/env python3
"""Pack a skeleton back out into a full-length game.

    uv run python scripts/build_game.py data/skeleton.json --seed 1 -o data/rebuilt.pgn

The skeleton alone is the input. If this produces a verified 17,697 ply then
the packer and the verifier are meshed, and from here any improvement to the
skeleton turns into a longer game for free.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import chess

from long_chess.filler import MAX_OCCURRENCES, pad_skeleton
from long_chess.skeleton import analyse, compress, load, to_pgn
from long_chess.verifier import repetition_key, verify_game


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_game")
    parser.add_argument(
        "skeleton", type=Path, help="skeleton JSON from extract_skeleton.py"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-restarts", type=int, default=8)
    parser.add_argument("-o", "--output", type=Path, help="write the game as PGN")
    parser.add_argument(
        "--expect-plies", type=int, help="fail unless the game is this long"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    skeleton = load(args.skeleton)
    stats = analyse(skeleton)
    print(
        f"skeleton    {skeleton.plies} ply, {skeleton.critical_count} segments, "
        f"worth {stats.achievable_plies} packed"
    )

    started = time.perf_counter()
    padded, report = pad_skeleton(
        skeleton, seed=args.seed, max_restarts=args.max_restarts
    )
    elapsed = time.perf_counter() - started

    restarts = report.total_attempts - len(report.attempts)
    print(f"packed      {padded.plies} ply in {elapsed:.1f}s, {restarts} restart(s)")
    if report.failures:
        print(
            f"FAIL: {len(report.failures)} segment(s) would not fill: "
            f"{list(report.failures)}",
            file=sys.stderr,
        )
        return 1

    padded_stats = analyse(padded)
    if padded_stats.slack:
        print(f"FAIL: {padded_stats.slack} ply of slack remains", file=sys.stderr)
        return 1
    print("slack       0, every segment packed to its target")

    if compress(padded).moves != skeleton.moves:
        print("FAIL: the packed game does not compress back", file=sys.stderr)
        return 1
    print("round trip  cancelling the filler returns the skeleton")

    result = verify_game(list(padded.moves))
    print(
        f"verified    {result.plies} ply, {result.termination.value}, "
        f"{result.critical_count} critical segments"
    )

    board = chess.Board(padded.start_fen)
    counts: Counter = Counter([repetition_key(board)])
    for move in padded.moves:
        board.push(move)
        counts[repetition_key(board)] += 1
    print(
        f"repetition  max {max(counts.values())} of {MAX_OCCURRENCES} allowed, "
        f"{len(counts)} distinct positions"
    )

    print()
    print(padded_stats.format_report())

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            to_pgn(
                padded,
                Event="Rebuilt from the critical skeleton",
                Site=f"packed, seed {args.seed}",
                Result="1-0",
            ),
            encoding="utf-8",
        )
        print(f"\nwrote {args.output}")

    if args.expect_plies is not None and result.plies != args.expect_plies:
        print(
            f"FAIL: expected {args.expect_plies} plies, got {result.plies}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
