"""Verify a PGN and report, optionally dumping the per-ply trace.

uv run python -m long_chess.verifier data/longest.pgn --trace out.tsv
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .game import VerificationError, verify_game
from .pgn import moves_from_pgn
from .rules import Termination
from .trace import write_jsonl, write_tsv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="long_chess.verifier")
    parser.add_argument("pgn", type=Path, help="PGN file to verify")
    parser.add_argument(
        "--trace",
        type=Path,
        help="write the per-ply log here (.jsonl for JSON Lines, else TSV)",
    )
    parser.add_argument(
        "--expect-plies",
        type=int,
        help="fail unless the game is exactly this many ply",
    )
    parser.add_argument(
        "--expect-termination",
        choices=[t.value for t in Termination if t.is_over],
        help="fail unless the game ends this way",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    started = time.perf_counter()
    moves = moves_from_pgn(args.pgn)
    parsed = time.perf_counter()
    try:
        result = verify_game(moves, trace=args.trace is not None)
    except VerificationError as error:
        print(f"REJECTED: {error}", file=sys.stderr)
        return 1
    verified = time.perf_counter()

    print(f"plies              {result.plies}")
    print(f"termination        {result.termination.value}")
    print(f"critical segments  {result.critical_count}")
    print(f"final fen          {result.final_fen}")
    print(f"parse / verify     {parsed - started:.2f}s / {verified - parsed:.2f}s")

    if args.trace is not None and result.trace is not None:
        writer = write_jsonl if args.trace.suffix == ".jsonl" else write_tsv
        args.trace.parent.mkdir(parents=True, exist_ok=True)
        with open(args.trace, "w", encoding="utf-8") as stream:
            count = writer(result.trace, stream)
        print(f"trace              {count} records -> {args.trace}")

    failures = []
    if args.expect_plies is not None and result.plies != args.expect_plies:
        failures.append(f"expected {args.expect_plies} plies, got {result.plies}")
    if (
        args.expect_termination is not None
        and result.termination.value != args.expect_termination
    ):
        failures.append(
            f"expected {args.expect_termination}, got {result.termination.value}"
        )
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
