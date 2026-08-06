"""Why S cannot be 2, and what a construction would have to do about it.

The bound in :mod:`schedule` is computed for one event multiset. This module
turns the reason behind it into a counting argument that does not depend on the
particular events — which is what the optimality bound needs, and as far as
scheduling alone can take it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import chess

from .events import CriticalEvent


@dataclass(frozen=True, slots=True)
class Chain:
    """A ``W → B → W`` run of forced precedences.

    One of these is enough to put S at 3 or more. The blocks alternate, so a
    chain of three colours needs three of them, and the game opens as if Black
    had just moved: leading with White is already a switch, and leading with
    Black pushes the chain into a fourth block. Either way, three switches.
    """

    white_move: CriticalEvent
    black_capture: CriticalEvent
    white_recapture: CriticalEvent

    def describe(self) -> str:
        return (
            f"W {self.white_move.san} (#{self.white_move.index}) "
            f"-> B {self.black_capture.san} (#{self.black_capture.index}) "
            f"-> W {self.white_recapture.san} (#{self.white_recapture.index})"
        )


def find_chains(events: list[CriticalEvent]) -> list[Chain]:
    """Every ``W → B → W`` chain in an event multiset.

    The shape is always the same:

    1. a White piece makes a critical move,
    2. Black captures it — which must come after, since a piece moves before it
       is taken,
    3. White captures the capturer — which must come after that, for the same
       reason.
    """
    by_mover: dict[int, list[CriticalEvent]] = defaultdict(list)
    captured_at: dict[int, CriticalEvent] = {}
    for event in events:
        by_mover[event.mover].append(event)
        if event.victim is not None:
            captured_at[event.victim] = event

    chains: list[Chain] = []
    for event in events:
        if not event.is_capture or event.actor != chess.BLACK:
            continue
        white_moves = [
            move for move in by_mover.get(event.victim, []) if move.actor == chess.WHITE
        ]
        recapture = captured_at.get(event.mover)
        if white_moves and recapture is not None:
            chains.append(Chain(white_moves[-1], event, recapture))
    return chains


@dataclass(frozen=True, slots=True)
class KingCaptureRequirement:
    """What a construction with S ≤ 2 would have to arrange.

    Reasoning, for a game where White mates and so ends with king plus one
    piece:

    - Black has to capture 14 White pieces, leaving those two.
    - A Black capture creates a ``W → B`` precedence unless its victim has made
      no critical move at all. Quiet moves do not count: a rook that shuffles
      but never captures has no critical events, and taking it forces nothing.
    - At most 7 White pieces can have no critical events. All eight pawns must
      make their six moves each — that is where 96 of the 118 critical moves
      come from, and every pawn move given up costs a whole 150-ply segment —
      which leaves the seven non-king pieces.
    - So at least 14 − 7 = 7 Black captures take a White piece that has moved,
      and each of those creates a ``W → B``.
    - For none of them to extend to ``W → B → W``, the capturing Black piece
      must never itself be captured. Black ends with only its king, so every
      other Black piece is captured.

    Hence: **the Black king must personally make at least seven captures**, all
    of White pieces that have already made a critical move.

    Nothing here proves that is impossible. It is a hard, concrete condition,
    and checking it is the model's business.
    """

    black_captures_needed: int
    quiet_white_pieces_available: int
    """How many White pieces *could* have no critical move: always 7.

    White's sixteen are eight pawns and eight others. Every pawn must make its
    six moves, so none of them qualifies, and the king cannot be captured. That
    leaves the seven non-king, non-pawn pieces — and only if White does its own
    capturing with pawns and the king, since a piece that captures has critical
    events of its own.
    """

    quiet_white_pieces_used: int
    """How many of that allowance this multiset actually spends."""

    forced_king_captures: int
    actual_king_captures: int

    @property
    def satisfied(self) -> bool:
        return self.actual_king_captures >= self.forced_king_captures

    def describe(self) -> str:
        return (
            f"Black must capture {self.black_captures_needed} White pieces. A "
            "capture forces nothing only if its victim never made a critical "
            f"move, and at most {self.quiet_white_pieces_available} White "
            "pieces can be in that state — the eight pawns all have to make "
            "their six moves, and the king cannot be taken. So at least "
            f"{self.forced_king_captures} of Black's captures take a White "
            "piece that has moved, and each of those must be made by the Black "
            "king, since every other Black piece is itself captured later. The "
            f"known game spends {self.quiet_white_pieces_used} of the "
            f"allowance and has {self.actual_king_captures} king captures."
        )


QUIET_WHITE_PIECES = 7
"""White pieces that can avoid having any critical move: the non-king,
non-pawn ones. All eight pawns must move; the king cannot be captured."""


def king_capture_requirement(events: list[CriticalEvent]) -> KingCaptureRequirement:
    """The counting argument, evaluated against an actual event multiset."""
    black_captures = [
        event for event in events if event.is_capture and event.actor == chess.BLACK
    ]

    movers_with_events = {event.mover for event in events if event.actor == chess.WHITE}
    quiet_used = sum(
        1 for event in black_captures if event.victim not in movers_with_events
    )

    captured = {event.victim for event in events if event.victim is not None}
    king_captures = sum(1 for event in black_captures if event.mover not in captured)

    return KingCaptureRequirement(
        black_captures_needed=len(black_captures),
        quiet_white_pieces_available=QUIET_WHITE_PIECES,
        quiet_white_pieces_used=quiet_used,
        forced_king_captures=max(0, len(black_captures) - QUIET_WHITE_PIECES),
        actual_king_captures=king_captures,
    )
