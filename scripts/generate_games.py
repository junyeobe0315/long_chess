#!/usr/bin/env python3
"""Generate many games from one skeleton and verify every one.

    uv run python scripts/generate_games.py data/skeleton.json -n 300 -o data/m3

The point is not the games. It is that packing a skeleton hundreds of ways is a
large randomised test of the packer *and* the verifier — a single game passing
says much less than three hundred passing — and that where the packer has to
work hard is the data a rescheduling attempt would need.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from long_chess.filler import pad_skeleton
from long_chess.skeleton import analyse, compress, load
from long_chess.verifier import Termination, verify_game

SKELETON: object = None


@dataclass(frozen=True)
class Run:
    seed: int
    plies: int
    termination: str
    critical_count: int
    slack: int
    restarts: int
    failures: tuple[int, ...]
    digest: str
    skeleton_preserved: bool
    compressed_plies: int
    seconds: float
    anchors_per_insertion: tuple[float, ...]
    dfs_fallbacks: tuple[int, ...]
    walks_by_length: dict[str, int]


def _preserves(recovered, original) -> bool:
    """Whether cancelling the filler gives back an equivalent skeleton.

    Not the *same* one: cancellation is greedy and not canonical, so different
    filler can leave different irreducible bridges. What must survive is
    everything the objective is made of -- which critical moves are played, in
    what order, by whom.
    """
    return (
        recovered.critical_sans() == original.critical_sans()
        and recovered.actors == original.actors
        and analyse(recovered).score[:2] == analyse(original).score[:2]
    )


def _init(skeleton_path: str) -> None:
    """Load the skeleton once per worker rather than shipping it per task."""
    global SKELETON
    SKELETON = load(skeleton_path)


def _run(seed: int) -> Run:
    skeleton = SKELETON
    started = time.perf_counter()
    padded, report = pad_skeleton(skeleton, seed=seed, collect_stats=True)
    elapsed = time.perf_counter() - started

    moves = list(padded.moves)
    result = verify_game(moves)
    stats = analyse(padded)
    recovered = compress(padded)

    by_length: dict[str, int] = {}
    for segment_stats in report.stats:
        for length, count in segment_stats.by_length.items():
            by_length[str(length)] = by_length.get(str(length), 0) + count

    digest = hashlib.sha256(" ".join(move.uci() for move in moves).encode()).hexdigest()

    return Run(
        seed=seed,
        plies=result.plies,
        termination=result.termination.value,
        critical_count=result.critical_count,
        slack=stats.slack,
        restarts=report.total_attempts - len(report.attempts),
        failures=report.failures,
        digest=digest,
        skeleton_preserved=_preserves(recovered, skeleton),
        compressed_plies=recovered.plies,
        seconds=elapsed,
        anchors_per_insertion=tuple(
            round(s.anchors_per_insertion, 4) for s in report.stats
        ),
        dfs_fallbacks=tuple(s.dfs_fallbacks for s in report.stats),
        walks_by_length=by_length,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="generate_games")
    parser.add_argument("skeleton", type=Path)
    parser.add_argument("-n", "--count", type=int, default=100)
    parser.add_argument("--start-seed", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("-o", "--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    skeleton = load(args.skeleton)
    expected = analyse(skeleton).achievable_plies
    seeds = list(range(args.start_seed, args.start_seed + args.count))
    print(f"skeleton worth {expected} ply; generating {len(seeds)} games")

    started = time.perf_counter()
    runs: list[Run] = []
    with ProcessPoolExecutor(
        max_workers=args.workers, initializer=_init, initargs=(str(args.skeleton),)
    ) as pool:
        for done, run in enumerate(pool.map(_run, seeds, chunksize=2), start=1):
            runs.append(run)
            if done % 25 == 0 or done == len(seeds):
                rate = done / (time.perf_counter() - started)
                print(f"  {done}/{len(seeds)}  ({rate:.1f} games/s)", flush=True)
    elapsed = time.perf_counter() - started

    path = args.output / "runs.jsonl"
    with open(path, "w", encoding="utf-8") as stream:
        for run in runs:
            stream.write(json.dumps(asdict(run)) + "\n")

    bad = [
        run
        for run in runs
        if run.plies != expected
        or run.termination != Termination.CHECKMATE.value
        or run.slack
        or run.failures
        or not run.skeleton_preserved
    ]
    digests = {run.digest for run in runs}

    print()
    print(f"generated   {len(runs)} games in {elapsed:.1f}s")
    good = len(runs) - len(bad)
    print(f"all {expected} ply, checkmate, zero slack: {good}/{len(runs)}")
    print(f"distinct    {len(digests)} of {len(runs)}")
    print(f"restarts    {sum(run.restarts for run in runs)} across all runs")
    lengths = sorted({run.compressed_plies for run in runs})
    print(f"recompress  to {lengths} ply (289 is the skeleton we started from)")
    print(f"wrote {path}")

    if bad:
        print(f"\nFAIL: {len(bad)} run(s) did not check out", file=sys.stderr)
        for run in bad[:5]:
            print(f"  seed {run.seed}: {run}", file=sys.stderr)
        return 1
    if len(digests) != len(runs):
        print("\nFAIL: duplicate games", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
