"""Pins the known gap in our termination checking.

See docs/dead-positions.md. These tests assert what the verifier *does*, gap
included, so that the day python-chess changes behaviour we find out here
rather than inside a maximality proof.
"""

from __future__ import annotations

import chess
import pytest

from long_chess.verifier import Termination, classify_position

# Every pawn is blocked by the pawn in front of it and has no diagonal contact
# with any other, so no pawn can ever move again and neither king can be mated.
# Dead under FIDE 5.2.2.
LOCKED_PAWNS = "7k/8/8/p1p1p1p1/P1P1P1P1/8/8/K7 w - - 0 1"


def test_the_locked_position_really_is_locked():
    """Precondition for the gap below: no pawn of either colour can move."""
    for turn in (chess.WHITE, chess.BLACK):
        board = chess.Board(LOCKED_PAWNS)
        board.turn = turn
        pawn_moves = [
            move
            for move in board.legal_moves
            if board.piece_at(move.from_square).piece_type == chess.PAWN
        ]
        assert pawn_moves == []


def test_a_dead_position_is_not_detected():
    """The documented gap, asserted so a change in behaviour is loud."""
    board = chess.Board(LOCKED_PAWNS)
    assert not board.is_insufficient_material()
    assert classify_position(board, repetitions=1) is Termination.CONTINUE


@pytest.mark.parametrize(
    ("fen", "detected"),
    [
        ("7k/8/8/8/8/8/8/K7 w - - 0 1", True),  # K vs K
        ("7k/8/8/8/8/8/8/KB6 w - - 0 1", True),  # K+B vs K
        ("7k/8/8/8/8/8/8/KN6 w - - 0 1", True),  # K+N vs K
        ("6bk/8/8/8/8/8/8/KB6 w - - 0 1", True),  # same-colour bishops
        ("7k/8/8/8/8/8/8/KNN5 w - - 0 1", False),  # K+N+N vs K: mate possible
        ("6bk/8/8/8/8/8/8/K1B5 w - - 0 1", False),  # opposite-colour bishops
        ("7k/8/8/8/8/8/8/KR6 w - - 0 1", False),  # K+R vs K
    ],
)
def test_material_only_classification(fen: str, detected: bool):
    assert chess.Board(fen).is_insufficient_material() is detected


def test_the_error_is_one_sided():
    """Detected implies dead, never the reverse.

    That direction is what makes the gap safe for the construction side:
    the test can only end
    a game later than FIDE would, so a game we verify is still a valid lower
    bound on the maximum length. The upper bound is where it has to be closed.
    """
    assert chess.Board("7k/8/8/8/8/8/8/K7 w - - 0 1").is_insufficient_material()
    assert not chess.Board(LOCKED_PAWNS).is_insufficient_material()
