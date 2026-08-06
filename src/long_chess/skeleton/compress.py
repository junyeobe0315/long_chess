"""Cycle cancellation: taking the filler back out of a padded game.

If a position occurs twice inside a bridge, the moves in between form a closed
walk. Deleting them leaves a legal game, because the position a move is played
from is exactly what ``repetition_key`` records — placement, side to move,
castling rights, and any *legal* en-passant right. Nothing else affects which
moves are available.

What deletion does change is the halfmove clock and the repetition counts, both
downward. That is the point: it is what turns a 150-ply segment back into the
handful of moves that actually do the work.

Cancellation runs inside a segment and never across one. Across segments it
would be pointless anyway — critical moves are irreversible, so no position can
recur — but scanning per segment keeps that assumption checkable rather than
assumed. :func:`find_cross_segment_repeats` is the check.
"""

from __future__ import annotations

import chess

from ..verifier import RepetitionKey, repetition_key
from .segment import Segment, Skeleton


def cancel_cycles(segment: Segment) -> Segment:
    """Remove every closed walk from a segment's bridge.

    Greedy and single-pass: each time the walk revisits a position, everything
    since that position is dropped. This is not guaranteed minimal — a shorter
    bridge might exist that this pass cannot see — but it removes all inserted
    filler, which is what skeleton extraction needs.
    """
    board = segment.board_at_start()
    kept: list[chess.Move] = []
    # Maps a position to the number of kept moves that reach it.
    seen: dict[RepetitionKey, int] = {repetition_key(board): 0}

    for move in segment.bridge_moves:
        board.push(move)
        kept.append(move)
        key = repetition_key(board)

        previous = seen.get(key)
        if previous is None:
            seen[key] = len(kept)
            continue

        # Closed walk: rewind to where this position first occurred.
        for _ in range(len(kept) - previous):
            board.pop()
        del kept[previous:]
        seen = {k: v for k, v in seen.items() if v <= previous}

    return segment.with_bridge(kept)


def compress(skeleton: Skeleton) -> Skeleton:
    """Cancel cycles in every segment.

    Segments are independent, so this is a plain map. The critical moves, their
    order, and their actors all come through untouched -- see
    :meth:`Skeleton.critical_sans`.
    """
    return Skeleton(
        tuple(cancel_cycles(segment) for segment in skeleton.segments),
        ends_in_checkmate=skeleton.ends_in_checkmate,
    )


def potential(board: chess.Board) -> tuple[int, int]:
    """``(pieces on the board, total pawn steps still available)``.

    This is why segments are independent, and the argument is short enough to
    give in full.

    Order the pairs lexicographically. Then:

    - A **quiet move** is neither a capture nor a pawn move, so it changes
      neither component. The potential is *constant* within a segment.
    - A **capture** removes a piece, so the first component drops. En passant
      included.
    - A **pawn move** keeps the piece count (promotion replaces the pawn rather
      than adding to it) and always reduces the second component: a push of one
      or two squares spends that many steps, and a promotion spends the pawn's
      last one.

    So the potential strictly decreases at every critical move and never moves
    otherwise. Two positions in different segments therefore have different
    potentials, so different placements, so different repetition keys — they
    cannot be the same position.

    That is what licenses counting repetitions per segment instead of across
    the whole game, which in turn is what lets the packer fill 118 segments
    independently.
    """
    pieces = chess.popcount(board.occupied)
    steps = 0
    for colour in (chess.WHITE, chess.BLACK):
        for square in board.pieces(chess.PAWN, colour):
            rank = chess.square_rank(square)
            steps += (7 - rank) if colour == chess.WHITE else rank
    return (pieces, steps)


def find_cross_segment_repeats(skeleton: Skeleton) -> list[tuple[int, int, str]]:
    """Positions occurring in two different segments, which should be none.

    Segment independence rests on critical moves being irreversible: a pawn
    cannot move back and a captured piece cannot return. If this ever returns a
    non-empty list, that reasoning has a hole and per-segment repetition
    counting is unsound.

    Returns ``(first segment index, second segment index, FEN)`` triples.
    """
    first_seen: dict[RepetitionKey, int] = {}
    repeats: list[tuple[int, int, str]] = []

    for index, segment in enumerate(skeleton.segments):
        board = segment.board_at_start()
        positions = [board.copy(stack=False)]
        for move in segment.moves:
            board.push(move)
            positions.append(board.copy(stack=False))
        # The closing position belongs to the next segment's start; skip it so
        # the shared boundary is not reported as a repeat.
        for position in positions[:-1]:
            key = repetition_key(position)
            previous = first_seen.setdefault(key, index)
            if previous != index:
                repeats.append((previous, index, position.fen()))

    return repeats
