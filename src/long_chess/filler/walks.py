"""Finding closed quiet walks — the filler that stretches a bridge out.

A walk is usable only if it returns to *exactly* the position it left, as
``repetition_key`` measures it. That rules out more than it first appears: a
rook stepping off a1 and back has not restored the position if it gave up a
castling right on the way, and the key correctly says so.

Search order matters for speed. Enumerate the cheap shapes first and only fall
back to a general search when they fail:

1. 4 ply, ``A B A⁻¹ B⁻¹`` — each side moves a piece out and back
2. 6 ply, both sides walking a 3-cycle
3. a bounded DFS, for when the board is too cramped for either
"""

from __future__ import annotations

import random
from collections.abc import Iterator

import chess

from ..verifier import RepetitionKey, repetition_key

MAX_OCCURRENCES = 4
"""A position may occur four times. The fifth ends the game."""


def quiet_moves(board: chess.Board) -> Iterator[chess.Move]:
    """Legal moves that filler is allowed to use.

    Excluded, and why:

    - **pawn moves and captures** reset the halfmove clock, which would split
      the segment in two and destroy the very structure we are packing.
    - **castling** does not reset the clock, so it is legal filler in
      principle. It is excluded anyway because it changes castling rights
      irreversibly: the position afterwards can never be returned to, so every
      walk through it is a dead end. Keeping it out is simpler than detecting
      that later.

    Leaving one's own king in check is already impossible — these are legal
    moves. Checks *given* are fine and the published game's filler uses them.
    """
    for move in board.legal_moves:
        if board.is_capture(move):
            continue
        piece = board.piece_at(move.from_square)
        if piece is not None and piece.piece_type == chess.PAWN:
            continue
        if board.is_castling(move):
            continue
        yield move


def is_usable_position(board: chess.Board) -> bool:
    """Whether filler may pass through this position.

    Checkmate and stalemate end the game, so a walk cannot go through them
    however briefly. Material cannot change inside filler, so there is nothing
    to check about insufficient material.
    """
    return not board.is_checkmate() and not board.is_stalemate()


def reverse(move: chess.Move) -> chess.Move:
    return chess.Move(move.to_square, move.from_square)


class WalkBudget:
    """Repetition counts for one segment, and what they still allow.

    Inserting a walk of length L at a position adds the walk's L-1
    intermediate positions *and* one more occurrence of the anchor, since the
    walk both leaves it and returns to it.
    """

    def __init__(self, counts: dict[RepetitionKey, int]) -> None:
        self.counts = counts

    def room(self, key: RepetitionKey, extra: int = 1) -> bool:
        return self.counts.get(key, 0) + extra <= MAX_OCCURRENCES

    def admits(self, keys: list[RepetitionKey]) -> bool:
        """Whether every key in a proposed walk still fits."""
        pending: dict[RepetitionKey, int] = {}
        for key in keys:
            pending[key] = pending.get(key, 0) + 1
        return all(self.room(key, extra) for key, extra in pending.items())


def find_four_ply_walk(
    board: chess.Board,
    budget: WalkBudget,
    rng: random.Random,
) -> list[chess.Move] | None:
    """``A B A⁻¹ B⁻¹``: White moves a piece out, Black too, then both back.

    The workhorse. Most of the published game's filler is this shape — segment
    0's 149-ply bridge is nothing but knights stepping out and back.

    Both pieces must stay out of each other's way: if Black occupies the square
    White vacated, White cannot return, and the legality checks catch it.
    """
    start_key = repetition_key(board)
    if not budget.room(start_key):
        return None

    first_moves = list(quiet_moves(board))
    rng.shuffle(first_moves)

    for a in first_moves:
        board.push(a)
        if is_usable_position(board):
            key_a = repetition_key(board)
            replies = list(quiet_moves(board))
            rng.shuffle(replies)
            for b in replies:
                board.push(b)
                walk = _close_four_ply(board, a, b, start_key, key_a, budget)
                board.pop()
                if walk is not None:
                    board.pop()
                    return walk
        board.pop()
    return None


def _close_four_ply(
    board: chess.Board,
    a: chess.Move,
    b: chess.Move,
    start_key: RepetitionKey,
    key_a: RepetitionKey,
    budget: WalkBudget,
) -> list[chess.Move] | None:
    """Try to finish ``a b`` with ``a⁻¹ b⁻¹``. ``board`` is after ``a b``."""
    if not is_usable_position(board):
        return None
    key_ab = repetition_key(board)

    a_back = reverse(a)
    if a_back not in board.legal_moves or board.is_capture(a_back):
        return None
    board.push(a_back)
    try:
        if not is_usable_position(board):
            return None
        key_aba = repetition_key(board)

        b_back = reverse(b)
        if b_back not in board.legal_moves or board.is_capture(b_back):
            return None
        board.push(b_back)
        try:
            if repetition_key(board) != start_key:
                return None
            if not budget.admits([key_a, key_ab, key_aba, start_key]):
                return None
            return [a, b, a_back, b_back]
        finally:
            board.pop()
    finally:
        board.pop()


def find_six_ply_walk(
    board: chess.Board,
    budget: WalkBudget,
    rng: random.Random,
) -> list[chess.Move] | None:
    """Both sides walk one piece round a 3-cycle, interleaved.

    Needed for arithmetic, not variety: 4-ply walks alone can only build
    multiples of 4, so a bridge needing 6, 10, 14 … more ply is unreachable
    without one of these. See :func:`plan_lengths`.
    """
    start_key = repetition_key(board)
    if not budget.room(start_key):
        return None

    firsts = list(quiet_moves(board))
    rng.shuffle(firsts)

    for w1 in firsts:
        board.push(w1)
        if is_usable_position(board):
            replies = list(quiet_moves(board))
            rng.shuffle(replies)
            for b1 in replies:
                board.push(b1)
                if is_usable_position(board):
                    walk = _close_six_ply(board, w1, b1, start_key, budget, rng)
                    if walk is not None:
                        board.pop()
                        board.pop()
                        return walk
                board.pop()
        board.pop()
    return None


def _close_six_ply(
    board: chess.Board,
    w1: chess.Move,
    b1: chess.Move,
    start_key: RepetitionKey,
    budget: WalkBudget,
    rng: random.Random,
) -> list[chess.Move] | None:
    """Complete two 3-cycles. ``board`` is after ``w1 b1``, White to move."""
    keys = [repetition_key(_undo(board, 1)), repetition_key(board)]

    seconds = [m for m in quiet_moves(board) if m.from_square == w1.to_square]
    rng.shuffle(seconds)

    for w2 in seconds:
        board.push(w2)
        if is_usable_position(board):
            key_w2 = repetition_key(board)
            b_seconds = [m for m in quiet_moves(board) if m.from_square == b1.to_square]
            rng.shuffle(b_seconds)
            for b2 in b_seconds:
                board.push(b2)
                if is_usable_position(board):
                    key_b2 = repetition_key(board)
                    w3 = chess.Move(w2.to_square, w1.from_square)
                    if w3 in board.legal_moves and not board.is_capture(w3):
                        board.push(w3)
                        if is_usable_position(board):
                            key_w3 = repetition_key(board)
                            b3 = chess.Move(b2.to_square, b1.from_square)
                            if b3 in board.legal_moves and not board.is_capture(b3):
                                board.push(b3)
                                closed = repetition_key(board) == start_key
                                board.pop()
                                if closed and budget.admits(
                                    [*keys, key_w2, key_b2, key_w3, start_key]
                                ):
                                    board.pop()
                                    board.pop()
                                    board.pop()
                                    return [w1, b1, w2, b2, w3, b3]
                        board.pop()
                board.pop()
        board.pop()
    return None


def _undo(board: chess.Board, plies: int) -> chess.Board:
    """A copy of ``board`` with the last ``plies`` moves taken back."""
    probe = board.copy()
    for _ in range(plies):
        probe.pop()
    return probe


def find_walk_dfs(
    board: chess.Board,
    length: int,
    budget: WalkBudget,
    rng: random.Random,
    *,
    node_limit: int = 20_000,
) -> list[chess.Move] | None:
    """General bounded search, for when the shaped enumerators come up empty.

    Only reached on cramped boards — a late segment with few pieces left, or a
    king with no room. Slow is acceptable here; failing is not, because a
    segment that cannot be filled loses ply off the whole game.

    The prune is the placement distance: a quiet move changes exactly two
    squares, so a position differing from the start in more than ``2 ×
    remaining`` squares cannot get back in time.
    """
    start_key = repetition_key(board)
    if not budget.room(start_key):
        return None
    start_placement = board.board_fen()
    nodes = 0
    path: list[chess.Move] = []
    keys: list[RepetitionKey] = []

    def difference(placement: str) -> int:
        pairs = zip(placement, start_placement, strict=False)
        return sum(1 for a, b in pairs if a != b)

    def search(remaining: int) -> bool:
        nonlocal nodes
        if remaining == 0:
            return repetition_key(board) == start_key and budget.admits(
                [*keys[:-1], start_key]
            )
        if nodes >= node_limit:
            return False

        moves = list(quiet_moves(board))
        rng.shuffle(moves)
        for move in moves:
            nodes += 1
            if nodes >= node_limit:
                return False
            board.push(move)
            try:
                if not is_usable_position(board):
                    continue
                # Expanding the placement into a padded 64-char board is
                # overkill; the FEN difference is a cheap proxy that never
                # under-estimates by more than a constant.
                if remaining > 1 and difference(board.board_fen()) > 4 * (
                    remaining - 1
                ):
                    continue
                path.append(move)
                keys.append(repetition_key(board))
                if search(remaining - 1):
                    return True
                path.pop()
                keys.pop()
            finally:
                board.pop()
        return False

    return list(path) if search(length) else None


def find_closed_walk_traced(
    board: chess.Board,
    length: int,
    budget: WalkBudget,
    rng: random.Random,
) -> tuple[list[chess.Move] | None, str | None]:
    """A closed walk, plus which method found it.

    The method name is what the batch analysis uses to see where the packer
    is working hard: a
    segment falling through to ``dfs`` is one where the shaped enumerators
    found nothing, which is the signal that a position is running out of room.
    """
    if length % 2:
        raise ValueError(f"a closed walk has even length, not {length}")
    if length == 4:
        walk = find_four_ply_walk(board, budget, rng)
        if walk is not None:
            return walk, "four"
    elif length == 6:
        walk = find_six_ply_walk(board, budget, rng)
        if walk is not None:
            return walk, "six"
    walk = find_walk_dfs(board, length, budget, rng)
    return (walk, "dfs") if walk is not None else (None, None)


def find_closed_walk(
    board: chess.Board,
    length: int,
    budget: WalkBudget,
    rng: random.Random,
) -> list[chess.Move] | None:
    """A closed quiet walk of exactly ``length`` ply, or None."""
    return find_closed_walk_traced(board, length, budget, rng)[0]
