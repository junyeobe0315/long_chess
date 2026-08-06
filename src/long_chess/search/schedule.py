"""Scheduling the critical events, and a lower bound on S.

Since an event's actor is fixed by the piece it involves, S is decided purely
by the order the events are played in. That makes it a scheduling problem: 118
coloured tasks, some of which must precede others, and we want as few colour
changes as possible.

The precedence graph here holds **only necessary conditions** — constraints
that every legal game with this event multiset must satisfy. It is therefore a
relaxation: the real game's order is one of its topological orders, but not
every topological order is realisable. So the minimum number of colour blocks
over the relaxation is a **lower bound** on S, and if that bound is 3 then 3 is
optimal and 17,697 cannot be beaten *with these events*.

Which is the honest scope, and the limit of what scheduling alone can
settle. A different
choice of which pieces get captured, or of how the pawns route past each other,
is a different multiset with its own bound. Quantifying over all of them is
the optimality bound's job.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import chess

from .events import CriticalEvent, EventKind

PAWN_KINDS = (EventKind.PAWN, EventKind.PROMOTION, EventKind.PAWN_CAPTURE)


@dataclass(frozen=True, slots=True)
class Dependency:
    before: int
    after: int
    reason: str


def build_dependencies(events: list[CriticalEvent]) -> list[Dependency]:
    """Precedences every legal game with these events has to respect.

    Three families, and nothing else — omitting a real constraint only weakens
    the bound, so under-including is the safe direction:

    - **a pawn's moves are totally ordered.** A pawn's rank only increases, so
      it cannot take its third step before its second.
    - **a piece moves before it is captured.** Once taken it is off the board,
      so every event where it is the mover comes first. For a promoted piece
      this also puts its promotion before anything it does as a rook.
    - **the mate is last.**

    Deliberately left out: blocking. A pawn cannot advance onto an occupied
    square, which is a genuine constraint and a strong one, but it depends on
    where everything is at the time rather than on the events alone. Leaving it
    out keeps the graph sound.
    """
    dependencies: list[Dependency] = []
    by_mover: dict[int, list[CriticalEvent]] = defaultdict(list)
    captured_at: dict[int, CriticalEvent] = {}

    for event in events:
        by_mover[event.mover].append(event)
        if event.victim is not None:
            captured_at[event.victim] = event

    for mover, moves in by_mover.items():
        pawn_moves = [event for event in moves if event.kind in PAWN_KINDS]
        others = [event for event in moves if event.kind not in PAWN_KINDS]

        for earlier, later in zip(pawn_moves, pawn_moves[1:], strict=False):
            dependencies.append(
                Dependency(earlier.index, later.index, "a pawn advances in order")
            )

        # Anything the piece does after promoting must follow the promotion.
        if pawn_moves and others:
            last_pawn_move = pawn_moves[-1]
            for event in others:
                dependencies.append(
                    Dependency(
                        last_pawn_move.index,
                        event.index,
                        "a promoted piece exists only after promoting",
                    )
                )

        capture = captured_at.get(mover)
        if capture is not None:
            for event in moves:
                dependencies.append(
                    Dependency(
                        event.index,
                        capture.index,
                        "a piece moves before it is captured",
                    )
                )

    mate = next((event for event in events if event.kind is EventKind.MATE), None)
    if mate is not None:
        for event in events:
            if event.index != mate.index:
                dependencies.append(
                    Dependency(event.index, mate.index, "the mate ends the game")
                )

    return dependencies


@dataclass(frozen=True, slots=True)
class Schedule:
    """An assignment of events to alternating single-colour blocks."""

    first_colour: chess.Color
    block_of: tuple[int, ...]
    """Block index per event, in event order."""

    blocks: int

    @property
    def switches(self) -> int:
        """S, counting the virtual Black critical move before ply 1.

        A game opening with a Black block costs nothing; opening with White is
        already one switch.
        """
        return self.blocks - 1 if self.first_colour == chess.BLACK else self.blocks

    def block_sizes(self) -> list[int]:
        sizes = [0] * self.blocks
        for block in self.block_of:
            sizes[block] += 1
        return sizes


def schedule_from(
    events: list[CriticalEvent],
    dependencies: list[Dependency],
    first_colour: chess.Color,
) -> Schedule:
    """Fewest alternating blocks, given which colour goes first.

    Each event is put in the earliest block whose colour matches and which is
    at or after every predecessor's block. Taking the earliest everywhere is
    the least fixed point of the constraints, so it minimises every event's
    block at once and hence the total.
    """
    predecessors: dict[int, list[int]] = defaultdict(list)
    successors: dict[int, list[int]] = defaultdict(list)
    for dependency in dependencies:
        predecessors[dependency.after].append(dependency.before)
        successors[dependency.before].append(dependency.after)

    remaining = {event.index: len(predecessors[event.index]) for event in events}
    colour = {event.index: event.actor for event in events}
    block: dict[int, int] = {}

    ready = [index for index, count in remaining.items() if count == 0]
    order: list[int] = []
    while ready:
        index = ready.pop()
        order.append(index)
        for successor in successors[index]:
            remaining[successor] -= 1
            if remaining[successor] == 0:
                ready.append(successor)

    if len(order) != len(events):
        raise ValueError("the dependency graph has a cycle")

    for index in order:
        earliest = max((block[p] for p in predecessors[index]), default=0)
        wanted_parity = 0 if colour[index] == first_colour else 1
        if earliest % 2 != wanted_parity:
            earliest += 1
        block[index] = earliest

    blocks = max(block.values()) + 1
    return Schedule(
        first_colour=first_colour,
        block_of=tuple(block[event.index] for event in events),
        blocks=blocks,
    )


def best_schedule(
    events: list[CriticalEvent],
    dependencies: list[Dependency],
) -> Schedule:
    """The schedule with the fewest colour switches, over both starting colours."""
    candidates = [
        schedule_from(events, dependencies, chess.BLACK),
        schedule_from(events, dependencies, chess.WHITE),
    ]
    return min(candidates, key=lambda schedule: schedule.switches)


def critical_chain(
    events: list[CriticalEvent],
    dependencies: list[Dependency],
    schedule: Schedule,
) -> list[tuple[CriticalEvent, str]]:
    """A chain of events forcing the last block, with the reason at each step.

    This is the answer to "why can it not be done in fewer": walk back from an
    event in the final block through the predecessor that pushed it there.
    """
    by_index = {event.index: event for event in events}
    block_of = dict(zip((e.index for e in events), schedule.block_of, strict=True))
    incoming: dict[int, list[Dependency]] = defaultdict(list)
    for dependency in dependencies:
        incoming[dependency.after].append(dependency)

    last = max(by_index, key=lambda index: (block_of[index], index))
    chain: list[tuple[CriticalEvent, str]] = [(by_index[last], "in the final block")]

    current = last
    while True:
        pushers = [
            dependency
            for dependency in incoming[current]
            if block_of[dependency.before] >= block_of[current] - 1
        ]
        if not pushers:
            break
        pusher = max(pushers, key=lambda dependency: block_of[dependency.before])
        if block_of[pusher.before] == block_of[current] and current == pusher.before:
            break
        chain.append((by_index[pusher.before], pusher.reason))
        if block_of[pusher.before] == 0:
            break
        current = pusher.before

    return list(reversed(chain))
