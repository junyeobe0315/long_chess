#!/usr/bin/env python3
"""Try to break the home-rank lemma, which the optimality result rests on.

    uv run python scripts/attack_lemma.py

Three things happen here, and the first is the one that makes the other two
worth reading:

1. the same search runs with the lemma's restriction lifted, where a pawn *can*
   get through. If it fails there, it is not looking properly and its silence
   elsewhere means nothing;
2. it runs under the lemma's actual conditions;
3. every legal attacker move at every position visited is enumerated and
   checked, not just the one played.
"""

from __future__ import annotations

import argparse
import sys
import time

import chess

from long_chess.bound import audit, hunt, verify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="attack_lemma")
    parser.add_argument("--attempts", type=int, default=400)
    parser.add_argument("--plies", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    colours = ((chess.BLACK, "Black"), (chess.WHITE, "White"))
    failures = []

    print("control: the restriction lifted, where a pawn CAN get through")
    for attacker, name in colours:
        result = hunt(
            attacker,
            attempts=args.attempts,
            plies=args.plies,
            allow_pawn_captures=True,
            seed=args.seed,
        )
        ok = result.reached_home_rank and result.best_pawn_moves >= 6
        print(
            f"  {name:5s} best single-pawn moves {result.best_pawn_moves}, "
            f"reached home rank {result.reached_home_rank}"
            f"   {'search works' if ok else 'SEARCH IS BLIND'}"
        )
        if not ok:
            failures.append(f"{name}: control failed, the search cannot find a break")

    print()
    print("under the lemma's conditions")
    for attacker, name in colours:
        result = hunt(
            attacker,
            attempts=args.attempts,
            plies=args.plies,
            allow_pawn_captures=False,
            seed=args.seed,
        )
        print(
            f"  {name:5s} best single-pawn moves {result.best_pawn_moves} "
            f"(lemma says at most 4), reached home rank "
            f"{result.reached_home_rank}, home rank disturbed "
            f"{result.invariant_breaks} times"
        )
        if result.best_pawn_moves > 4 or result.reached_home_rank:
            failures.append(f"{name}: COUNTEREXAMPLE — the lemma is false")

    print()
    print("exhaustive: every legal attacker move at every position visited")
    for attacker, name in colours:
        started = time.perf_counter()
        report = audit(
            attacker, attempts=args.attempts, plies=args.plies, seed=args.seed
        )
        print(
            f"  {name:5s} {report.positions:,} positions, "
            f"{report.moves_checked:,} moves, {len(report.violations)} violations, "
            f"{report.en_passant_offers} en-passant offers "
            f"({time.perf_counter() - started:.1f}s)"
        )
        if report.violations:
            failures.append(f"{name}: {report.violations[0]}")
        if not report.home_rank_intact:
            failures.append(f"{name}: the defender's home rank was disturbed")

    print()
    print("the proof the searches were evidence for")
    for obligation in verify():
        print(obligation.describe())
        if not obligation.discharged:
            failures.append(f"obligation {obligation.tag} not discharged")

    print()
    if failures:
        print("FAIL:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("no counterexample found, and the search demonstrably can find one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
