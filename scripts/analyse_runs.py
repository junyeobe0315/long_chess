#!/usr/bin/env python3
"""Read the batch output and say where the packer works hardest.

uv run python scripts/analyse_runs.py data/m3/runs.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analyse_runs")
    parser.add_argument("runs", type=Path)
    parser.add_argument("--top", type=int, default=8)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runs = [json.loads(line) for line in args.runs.read_text().splitlines()]
    segments = len(runs[0]["anchors_per_insertion"])

    print(f"{len(runs)} runs, {segments} segments each")
    print()

    seconds = [run["seconds"] for run in runs]
    print(
        f"pack time      median {statistics.median(seconds):.1f}s, "
        f"max {max(seconds):.1f}s"
    )
    print(f"restarts       {sum(run['restarts'] for run in runs)} in total")
    print(f"distinct games {len({run['digest'] for run in runs})}/{len(runs)}")

    lengths: Counter = Counter()
    for run in runs:
        for length, count in run["walks_by_length"].items():
            lengths[int(length)] += count
    total = sum(lengths.values())
    print(
        f"walks inserted {total} across all runs: "
        + ", ".join(
            f"{n}×{k}-ply ({100 * n / total:.2f}%)" for k, n in sorted(lengths.items())
        )
    )

    dfs = sum(sum(run["dfs_fallbacks"]) for run in runs)
    print(f"DFS fallbacks  {dfs}")

    recompressed = Counter(run["compressed_plies"] for run in runs)
    print(f"recompresses to {dict(sorted(recompressed.items()))}")

    print()
    print("hardest segments, by mean anchors tried per insertion")
    print(f"{'seg':>4} {'mean':>7} {'max':>7}")
    means = []
    for index in range(segments):
        values = [run["anchors_per_insertion"][index] for run in runs]
        means.append((statistics.mean(values), max(values), index))
    for mean, worst, index in sorted(means, reverse=True)[: args.top]:
        print(f"{index:>4} {mean:>7.2f} {worst:>7.2f}")

    overall = statistics.mean(mean for mean, _, _ in means)
    print(
        f"\noverall mean anchors per insertion: {overall:.2f} "
        "(1.00 = the first anchor always worked)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
