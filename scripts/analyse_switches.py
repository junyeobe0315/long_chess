#!/usr/bin/env python3
"""How few colour switches can this skeleton's events be scheduled into?

    uv run python scripts/analyse_switches.py data/skeleton.json

Reports a lower bound on S, checks that the bound's precedence graph is sound
against the actual game, and — if the bound says 3 — names the chain that
forces it and the condition a better construction would have to meet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chess

from long_chess.search import (
    actor_counts,
    best_schedule,
    build_dependencies,
    critical_chain,
    extract_events,
    phases,
    schedule_from,
)
from long_chess.search.obstruction import find_chains, king_capture_requirement
from long_chess.skeleton import analyse, load

SEGMENT_TARGET = 150


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analyse_switches")
    parser.add_argument("skeleton", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    skeleton = load(args.skeleton)
    stats = analyse(skeleton)
    events = extract_events(skeleton)
    dependencies = build_dependencies(events)

    print(f"events        {len(events)}  {actor_counts(events)}")
    print(
        "observed      "
        + " -> ".join(f"{c}×{hi - lo + 1}" for c, lo, hi in phases(events))
        + f"   S = {stats.actor_switches}"
    )

    violated = [d for d in dependencies if d.before >= d.after]
    print(
        f"soundness     {len(violated)} of {len(dependencies)} precedences "
        "violated by the actual game (must be 0)"
    )
    if violated:
        for dependency in violated[:5]:
            print(
                f"  #{dependency.before} must precede #{dependency.after}: "
                f"{dependency.reason}",
                file=sys.stderr,
            )
        return 1

    print()
    for colour, name in ((chess.BLACK, "Black first"), (chess.WHITE, "White first")):
        schedule = schedule_from(events, dependencies, colour)
        print(
            f"{name:12s}  {schedule.blocks} blocks {schedule.block_sizes()}"
            f"  ->  S = {schedule.switches}"
        )

    best = best_schedule(events, dependencies)
    bound = SEGMENT_TARGET * len(events) - best.switches
    print()
    print(
        f"LOWER BOUND   S ≥ {best.switches}  ->  at most {bound} ply with these events"
    )
    print(f"achieved      S = {stats.actor_switches}  ->  {stats.achievable_plies} ply")
    if best.switches == stats.actor_switches:
        print("              the known construction is optimal for this multiset")

    print()
    print("forcing chain")
    for event, reason in critical_chain(events, dependencies, best):
        print(f"  {event.actor_name} {event.san:9s} (#{event.index:3d})  {reason}")

    chains = find_chains(events)
    print()
    print(f"W→B→W chains  {len(chains)}; any one of them forces S ≥ 3")
    for chain in chains[:4]:
        print(f"  {chain.describe()}")

    requirement = king_capture_requirement(events)
    print()
    print("what S ≤ 2 would need")
    for line in _wrap(requirement.describe()):
        print(f"  {line}")
    return 0


def _wrap(text: str, width: int = 74) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


if __name__ == "__main__":
    sys.exit(main())
