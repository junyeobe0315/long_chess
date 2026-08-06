"""Splitting a game into critical segments.

A *segment* runs from just after one critical move up to and including the
next. Everything before that closing move is the **bridge**: quiet moves that
set the next critical move up. Filler — the closed walks that stretch a segment
out to its 149/150 target — lives inside the bridge too, and the skeleton
extraction's job is to
take it back out.

The decomposition works because critical moves are irreversible: a pawn cannot
go back and a captured piece cannot return. So no position can occur in two
different segments, and each segment can be planned on its own.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

import chess

from ..verifier import is_critical


@dataclass(frozen=True, slots=True)
class Segment:
    """One critical segment.

    ``critical_move`` is a pawn move or a capture, except in the final segment
    of a game that ends in checkmate: mate outranks the 75-move draw, so it
    closes a segment even when it is neither.
    """

    start_fen: str
    bridge_moves: tuple[chess.Move, ...]
    critical_move: chess.Move

    @property
    def start_turn(self) -> chess.Color:
        return self.start_fen.split()[1] == "w"

    @property
    def actor(self) -> chess.Color:
        """Who plays the critical move.

        The bridge alternates colours, so its parity decides. This is the
        quantity S counts changes of.
        """
        if len(self.bridge_moves) % 2 == 0:
            return self.start_turn
        return not self.start_turn

    @property
    def length(self) -> int:
        """Plies in the segment, bridge plus the critical move."""
        return len(self.bridge_moves) + 1

    @property
    def moves(self) -> tuple[chess.Move, ...]:
        return (*self.bridge_moves, self.critical_move)

    def board_at_start(self) -> chess.Board:
        return chess.Board(self.start_fen)

    def with_bridge(self, bridge_moves: Iterable[chess.Move]) -> Segment:
        return replace(self, bridge_moves=tuple(bridge_moves))


@dataclass(frozen=True, slots=True)
class Skeleton:
    """A game as a sequence of segments."""

    segments: tuple[Segment, ...]
    ends_in_checkmate: bool

    @property
    def start_fen(self) -> str:
        return self.segments[0].start_fen

    @property
    def critical_count(self) -> int:
        """K in ``L = 150K - S - Σδ``."""
        return len(self.segments)

    @property
    def plies(self) -> int:
        return sum(segment.length for segment in self.segments)

    @property
    def moves(self) -> tuple[chess.Move, ...]:
        return tuple(move for segment in self.segments for move in segment.moves)

    @property
    def actors(self) -> tuple[chess.Color, ...]:
        return tuple(segment.actor for segment in self.segments)

    def critical_sans(self) -> tuple[str, ...]:
        """The closing moves in SAN, for comparing two skeletons.

        Two skeletons of the same game must agree here exactly: cycle
        cancellation may shorten bridges but must never touch which critical
        moves are played, in what order, by whom.
        """
        board = chess.Board(self.start_fen)
        out = []
        for segment in self.segments:
            for move in segment.bridge_moves:
                board.push(move)
            out.append(board.san(segment.critical_move))
            board.push(segment.critical_move)
        return tuple(out)


class SplitError(ValueError):
    """The move sequence does not decompose into critical segments."""


def split_game(
    moves: Iterable[chess.Move],
    board: chess.Board | None = None,
) -> Skeleton:
    """Split a full game into segments.

    The final move closes a segment whether or not it is critical, but only if
    it is checkmate — otherwise the trailing quiet moves belong to a segment
    that never ends, and the caller has handed us something that is not a
    finished game.
    """
    moves = list(moves)
    if not moves:
        raise SplitError("no moves")

    board = board.copy(stack=False) if board is not None else chess.Board()
    segments: list[Segment] = []
    start_fen = board.fen()
    bridge: list[chess.Move] = []

    for index, move in enumerate(moves):
        is_last = index == len(moves) - 1
        critical = is_critical(board, move)
        board.push(move)

        if critical or is_last:
            segments.append(Segment(start_fen, tuple(bridge), move))
            start_fen = board.fen()
            bridge = []
        else:
            bridge.append(move)

    if not board.is_checkmate() and not is_critical_close(segments[-1], moves):
        raise SplitError(
            "the game does not end in checkmate and its last move is not "
            "critical, so the final segment is unterminated"
        )

    return Skeleton(tuple(segments), ends_in_checkmate=board.is_checkmate())


def is_critical_close(segment: Segment, moves: list[chess.Move]) -> bool:
    """Whether the last segment was closed by a genuine critical move."""
    board = segment.board_at_start()
    for move in segment.bridge_moves:
        board.push(move)
    return is_critical(board, segment.critical_move)
