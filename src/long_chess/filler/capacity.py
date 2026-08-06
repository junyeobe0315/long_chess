"""How much filler a position can hold.

The rescheduling search wanted to reject a candidate skeleton before paying
to pack it. This module
was written to provide that test — and the measurements said it was barely
needed, which turned out to be an understatement: that search was replaced by a
proof and the test was never called in anger.

The finding, in short: capacity is close to
binary. Either a segment admits no closed walk at all, or it packs the
full 148/149 with room to spare. There is no middle ground to discriminate
against.

So the useful test is not "how much fits" but "does anything fit", and the
estimate below is deliberately crude in the **optimistic** direction: it
returns zero only when it can point at the reason, and otherwise assumes there
is room. An optimistic estimate wastes search on branches that turn out
unpackable. A pessimistic one discards branches that were fine, and a discarded
branch leaves no trace — which, in a project whose point is to establish
whether a better skeleton exists, is the error that cannot be caught.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import chess

from ..skeleton import Segment
from ..verifier import repetition_key
from .pad import pack
from .targets import MAX_QUIET, segment_target
from .walks import WalkBudget, find_closed_walk, quiet_moves

MEASURE_LIMIT = MAX_QUIET - 1
"""Cap for measurement. Even, because closed walks come in even lengths."""


def measure_capacity(
    board: chess.Board,
    rng: random.Random,
    *,
    limit: int = MEASURE_LIMIT,
) -> int:
    """Ply packable from this position **with nothing else to work with**.

    A standing start: the only anchor is the position itself. That makes this
    stricter than what a real segment faces, because a segment's bridge
    supplies further anchors and may itself unblock the start — see
    :func:`blocking_reason`.
    """
    moves = pack(board, limit, rng, best_effort=True)
    return len(moves or [])


def measure_segment_capacity(segment: Segment, rng: random.Random) -> int:
    """Ply packable into a real segment, bridge included.

    This is the quantity that matters: it is what the packer will actually be
    asked for.
    """
    moves = pack(
        segment.board_at_start(),
        segment_target(segment),
        rng,
        initial=segment.bridge_moves,
        best_effort=True,
    )
    return len(moves or [])


def reversible_movers(board: chess.Board) -> int:
    """Pieces with a quiet move whose round trip restores the position.

    Two things have to hold, and only the first is obvious:

    - the return move must be legal and quiet. A piece can be pinned to the
      square it just left, so this is checked on the board after the move with
      the turn flipped back.
    - the move must not forfeit a castling right. `Ra1-b1` and `Rb1-a1` are both
      perfectly legal, and the rook ends where it began, but the *position* has
      changed and never changes back. A walk through it can never close.
    """
    rights = board.clean_castling_rights()
    seen: set[int] = set()
    for move in quiet_moves(board):
        if move.from_square in seen:
            continue
        board.push(move)
        if board.clean_castling_rights() != rights:
            board.pop()
            continue
        probe = board.copy(stack=False)
        probe.turn = not probe.turn
        back = chess.Move(move.to_square, move.from_square)
        reversible = back in probe.legal_moves and not probe.is_capture(back)
        board.pop()
        if reversible:
            seen.add(move.from_square)
    return len(seen)


def blocking_reason(board: chess.Board) -> str | None:
    """Why no closed walk starts here, or None if one does.

    Four causes, all of which a single bridge ply usually clears:

    - **a legal en-passant right.** Only a double pawn push sets one, and
      filler contains no pawn moves, so the right vanishes on the first ply and
      cannot be restored. Nothing that leaves this position ever returns to it.
    - **check** — the side to move must answer it, and stepping back would
      re-expose the king, so nothing is reversible.
    - **castling rights** — the only quiet moves are a rook or king leaving
      home, forfeiting a right. Once the right is spent the same shuffle closes
      perfectly; it is the *first* trip that cannot.
    - **no reversible mover** for one side. Both are needed for the
      ``A B A⁻¹ B⁻¹`` shape.
    """
    if board.has_legal_en_passant():
        return "a legal en-passant right that no quiet move can restore"
    if board.is_check():
        return "side to move is in check"

    for colour, name in ((chess.WHITE, "white"), (chess.BLACK, "black")):
        probe = board.copy(stack=False)
        probe.turn = colour
        if reversible_movers(probe) == 0:
            if any(True for _ in quiet_moves(probe)):
                return f"{name}'s only quiet moves forfeit castling rights"
            return f"{name} has no quiet move at all"
    return None


@dataclass(frozen=True, slots=True)
class CapacityFeatures:
    """Cheap facts about a position that bear on how much filler it holds."""

    quiet_moves: int
    white_movers: int
    black_movers: int
    free_pieces: int
    """Non-king, non-pawn pieces, both colours."""

    blocked_by: str | None


def features(board: chess.Board) -> CapacityFeatures:
    """Measure a position without packing it."""
    white = board.copy(stack=False)
    white.turn = chess.WHITE
    black = board.copy(stack=False)
    black.turn = chess.BLACK
    return CapacityFeatures(
        quiet_moves=sum(1 for _ in quiet_moves(board)),
        white_movers=reversible_movers(white),
        black_movers=reversible_movers(black),
        free_pieces=sum(
            len(board.pieces(piece_type, colour))
            for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
            for colour in (chess.WHITE, chess.BLACK)
        ),
        blocked_by=blocking_reason(board),
    )


def has_closed_walk(board: chess.Board, rng: random.Random) -> bool:
    """Whether any closed quiet walk starts here, on an empty budget."""
    empty = WalkBudget({})
    return any(
        find_closed_walk(board.copy(stack=False), length, empty, rng) is not None
        for length in (4, 6)
    )


def estimate_capacity(
    board: chess.Board,
    rng: random.Random,
    *,
    limit: int = MEASURE_LIMIT,
) -> int:
    """An optimistic estimate of packable ply, without packing.

    Zero when no walk starts here at all; otherwise ``limit``, because the
    measurements found nothing in between. This is a weak bound on purpose —
    weak and optimistic beats sharp and occasionally pessimistic, for the
    reason in the module docstring.
    """
    return limit if has_closed_walk(board, rng) else 0


def is_packable(board: chess.Board, needed: int, rng: random.Random) -> bool:
    """The quick feasibility test.

    False is a real answer: nothing can be packed here. True only means no
    cheap reason was found to rule it out.
    """
    return needed == 0 or estimate_capacity(board, rng, limit=needed) >= needed


def position_occurrences(board: chess.Board, moves: list[chess.Move]) -> int:
    """The largest number of times any position occurs along ``moves``."""
    counts: dict = {}
    probe = board.copy(stack=False)
    counts[repetition_key(probe)] = 1
    for move in moves:
        probe.push(move)
        key = repetition_key(probe)
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values())
