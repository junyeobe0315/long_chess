"""What counts as "the same position".

Every bug here loses repetitions, and a game that loses repetitions is illegal
in a way nothing else will notice.
"""

from __future__ import annotations

import chess
import pytest

from long_chess.verifier import repetition_key


def key_after(fen: str, *sans: str) -> tuple:
    board = chess.Board(fen)
    for san in sans:
        board.push_san(san)
    return repetition_key(board)


def test_halfmove_clock_and_move_number_are_not_part_of_identity():
    """The whole reason we cannot just compare FENs."""
    early = chess.Board("4k3/8/8/8/8/8/8/R3K3 w Q - 0 1")
    late = chess.Board("4k3/8/8/8/8/8/8/R3K3 w Q - 87 44")
    assert early.fen() != late.fen()
    assert repetition_key(early) == repetition_key(late)


def test_side_to_move_is_part_of_identity():
    white = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    black = chess.Board("4k3/8/8/8/8/8/8/4K3 b - - 0 1")
    assert repetition_key(white) != repetition_key(black)


def test_piece_placement_is_part_of_identity():
    a = chess.Board("4k3/8/8/8/8/8/8/R3K3 w Q - 0 1")
    b = chess.Board("4k3/8/8/8/8/8/8/1R2K3 w - - 0 1")
    assert repetition_key(a) != repetition_key(b)


class TestEnPassant:
    """Only a *legal* en-passant right distinguishes two positions."""

    def test_double_push_with_no_capturer_is_not_a_new_position(self):
        """1.e4 sets ep_square but no black pawn can take: same position."""
        board = chess.Board()
        board.push_san("e4")
        assert board.ep_square is not None, "precondition: python-chess sets it"
        assert not board.has_legal_en_passant()

        # The same placement reached without a double push.
        same = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        assert repetition_key(board) == repetition_key(same)

    def test_legal_en_passant_is_a_different_position(self):
        with_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
        assert with_ep.has_legal_en_passant()

        without_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - - 0 2")
        assert not without_ep.has_legal_en_passant()

        assert repetition_key(with_ep) != repetition_key(without_ep)

    def test_en_passant_that_would_expose_the_king_is_not_a_right(self):
        """Capturing en passant here is illegal (it would leave the king in
        check along the rank), so the position must not be treated as distinct."""
        pinned = chess.Board("8/8/8/K1pP3r/8/8/8/7k w - c6 0 2")
        assert not pinned.has_legal_en_passant(), "precondition: ep is pinned off"

        plain = chess.Board("8/8/8/K1pP3r/8/8/8/7k w - - 0 2")
        assert repetition_key(pinned) == repetition_key(plain)


class TestCastlingRights:
    def test_losing_rights_makes_a_different_position(self):
        """Rook out and back: same placement, but the right is gone."""
        start = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        before = chess.Board(start)
        after = key_after(start, "Rh1g1", "Rh8g8", "Rg1h1", "Rg8h8")

        assert before.board_fen() == chess.Board(start).board_fen()
        assert repetition_key(before) != after, (
            "white and black both lost kingside rights; must not compare equal"
        )

    def test_unreachable_rights_are_masked_off(self):
        """A FEN may claim rights whose rook is not there. clean_castling_rights
        drops them, so such a position is identical to one without the claim."""
        claimed = chess.Board("4k3/8/8/8/8/8/8/4K2R w KQ - 0 1")
        honest = chess.Board("4k3/8/8/8/8/8/8/4K2R w K - 0 1")
        assert claimed.castling_rights != honest.castling_rights, (
            "precondition: the raw bitmasks differ"
        )
        assert repetition_key(claimed) == repetition_key(honest)


def test_key_is_hashable_and_stable():
    board = chess.Board()
    assert hash(repetition_key(board)) == hash(repetition_key(board))
    assert repetition_key(board) == repetition_key(chess.Board())


@pytest.mark.parametrize(
    "fen",
    [
        chess.STARTING_FEN,
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    ],
)
def test_key_components(fen: str):
    board = chess.Board(fen)
    placement, turn, castling, ep = repetition_key(board)
    assert placement == board.board_fen()
    assert turn == board.turn
    assert castling == int(board.clean_castling_rights())
    assert ep == (board.ep_square if board.has_legal_en_passant() else None)
