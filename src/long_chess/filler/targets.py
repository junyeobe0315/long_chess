"""How long a segment's bridge is allowed to be.

This one function is where S comes from. A segment can hold 149 reversible ply
plus its critical move — unless the colour making critical moves has just
changed, in which case parity costs exactly one and it can hold only 148.
"""

from __future__ import annotations

import chess

from ..skeleton import Segment

MAX_QUIET = 149
"""Most reversible ply a segment can hold. 150 would be the automatic draw."""


def quiet_target(start_turn: chess.Color, critical_actor: chess.Color) -> int:
    """Longest legal bridge for a segment with this start turn and actor.

    The bridge alternates colours, so its parity decides who is on move for the
    critical move:

    - actor differs from the side starting the segment → the bridge must be an
      odd number of ply, and the largest odd number at most 149 is 149.
    - actor is the same side → the bridge must be even, and the largest even
      number at most 149 is 148, because 150 is the automatic draw.

    The second case is exactly a switch: a segment starts with whoever did
    *not* make the previous critical move on the move, so ``start_turn ==
    critical_actor`` means the actor has changed. That is the one ply each
    switch costs.
    """
    if start_turn != critical_actor:
        return MAX_QUIET
    return MAX_QUIET - 1


def segment_target(segment: Segment) -> int:
    """The bridge length :func:`quiet_target` allows for this segment."""
    return quiet_target(segment.start_turn, segment.actor)


def padding_needed(segment: Segment) -> int:
    """Ply of filler still to insert. Always even — closed walks are even."""
    return segment_target(segment) - len(segment.bridge_moves)
