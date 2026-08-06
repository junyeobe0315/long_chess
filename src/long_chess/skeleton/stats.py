"""The numbers in ``L = 150K - S - Σδ``, read off a skeleton.

The same report describes a padded game and a bare skeleton; only one column
differs in meaning. For a finished game ``slack`` is δ, the ply a segment threw
away. For a compressed skeleton it is the padding the packer still has to insert.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from .segment import Skeleton

SEGMENT_TARGET = 150
"""Longest a segment can be: 149 reversible ply plus the critical move."""


@dataclass(frozen=True, slots=True)
class Phase:
    """A run of consecutive segments whose critical moves are the same colour."""

    actor: chess.Color
    first: int
    last: int

    @property
    def size(self) -> int:
        return self.last - self.first + 1

    @property
    def actor_name(self) -> str:
        return "W" if self.actor else "B"


@dataclass(frozen=True, slots=True)
class SkeletonStats:
    critical_count: int
    """K."""

    actor_switches: int
    """S. Counts the opening as if Black had made a critical move before ply 1."""

    slack: int
    """Σ(target - length). Zero for a maximally packed game."""

    plies: int
    segment_lengths: tuple[int, ...]
    segment_targets: tuple[int, ...]
    switch_segments: tuple[int, ...]
    """Segments whose actor differs from the previous one. These cost a ply
    each and are the only thing standing between 17,697 and 17,699."""

    phases: tuple[Phase, ...]

    @property
    def achievable_plies(self) -> int:
        """What this skeleton is worth once every segment is packed full."""
        return SEGMENT_TARGET * self.critical_count - self.actor_switches

    @property
    def score(self) -> tuple[int, int, int]:
        """Lexicographic objective: maximise K, then minimise S, then slack.

        A tuple, not a weighted sum. With weights it is far too easy to write
        coefficients under which losing a critical move (150 ply) looks like a
        fair trade for removing switches (1 ply each).
        """
        return (self.critical_count, -self.actor_switches, -self.slack)

    def format_report(self) -> str:
        lines = [
            f"K  (critical segments) : {self.critical_count}",
            f"S  (actor switches)    : {self.actor_switches}",
            f"Σδ (slack)             : {self.slack}",
            f"plies                  : {self.plies}",
            f"150K - S - Σδ          : {
                SEGMENT_TARGET * self.critical_count - self.actor_switches - self.slack
            }",
            f"achievable if packed   : {self.achievable_plies}",
            f"switch segments        : {list(self.switch_segments)}",
            "phases                 : "
            + " -> ".join(
                f"{phase.actor_name}×{phase.size}[{phase.first}..{phase.last}]"
                for phase in self.phases
            ),
        ]
        return "\n".join(lines)


def analyse(skeleton: Skeleton) -> SkeletonStats:
    """Compute K, S, Σδ, the switch segments and the phase structure.

    The opening is treated as if Black had just made a critical move: the game
    starts with White to move, so a first segment closed by White is already a
    switch. That convention is what makes every segment obey the same rule
    instead of the first one being special.
    """
    actors = skeleton.actors
    lengths = tuple(segment.length for segment in skeleton.segments)

    previous: chess.Color = chess.BLACK
    switches = 0
    slack = 0
    targets: list[int] = []
    switch_segments: list[int] = []

    for index, (actor, length) in enumerate(zip(actors, lengths, strict=True)):
        switched = actor != previous
        if switched:
            switches += 1
            switch_segments.append(index)
        target = SEGMENT_TARGET - switched  # a switch costs exactly one ply
        targets.append(target)
        slack += target - length
        previous = actor

    phases: list[Phase] = []
    for index, actor in enumerate(actors):
        if phases and phases[-1].actor == actor:
            phases[-1] = Phase(actor, phases[-1].first, index)
        else:
            phases.append(Phase(actor, index, index))

    return SkeletonStats(
        critical_count=len(skeleton.segments),
        actor_switches=switches,
        slack=slack,
        plies=skeleton.plies,
        segment_lengths=lengths,
        segment_targets=tuple(targets),
        switch_segments=tuple(switch_segments),
        phases=tuple(phases),
    )
