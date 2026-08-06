"""Where the automatic termination rules fire, and in what order.

The single most important test in this file is
``test_the_150th_quiet_move_may_still_be_checkmate``. The last move of a
maximal game is exactly that case, and getting the priority backwards costs a
ply and turns a win into a draw.
"""

from __future__ import annotations

import chess
import pytest

from long_chess.verifier import (
    FIVEFOLD_REPETITION_COUNT,
    SEVENTYFIVE_MOVE_PLY_LIMIT,
    GameAlreadyOver,
    GameVerifier,
    IllegalMove,
    Termination,
    repetition_key,
    verify_game,
)
from long_chess.verifier.pgn import moves_from_san

# White to move with the clock at 149. Ra8 is checkmate (the black king on g8
# is boxed in by its own f7/g7/h7 pawns); Ra2 is an ordinary quiet move. Both
# take the clock to 150.
BRINK = "6k1/5ppp/8/8/8/8/8/R6K w - - 149 100"

# The same, with a black pawn on a2 so the rook has a capture available.
BRINK_WITH_CAPTURE = "6k1/5ppp/8/8/8/8/p7/R6K w - - 149 100"


class TestSeventyFiveMoveRule:
    def test_the_150th_quiet_move_is_a_draw(self):
        verifier = GameVerifier(chess.Board(BRINK))
        assert verifier.push_uci("a1a2") is Termination.SEVENTYFIVE_MOVE_RULE
        assert verifier.board.halfmove_clock == SEVENTYFIVE_MOVE_PLY_LIMIT

    def test_the_150th_quiet_move_may_still_be_checkmate(self):
        """Checkmate outranks the 75-move draw. This is the last move of a
        maximal game."""
        verifier = GameVerifier(chess.Board(BRINK))
        assert verifier.push_uci("a1a8") is Termination.CHECKMATE
        assert verifier.board.halfmove_clock == SEVENTYFIVE_MOVE_PLY_LIMIT, (
            "the mating move did reach the limit; it is the priority that saves it"
        )

    def test_the_149th_quiet_move_continues(self):
        board = chess.Board(BRINK)
        board.set_fen(BRINK.replace(" 149 ", " 148 "))
        verifier = GameVerifier(board)
        assert verifier.push_uci("a1a2") is Termination.CONTINUE
        assert verifier.board.halfmove_clock == 149

    def test_a_capture_resets_the_clock(self):
        verifier = GameVerifier(chess.Board(BRINK_WITH_CAPTURE))
        assert verifier.push_uci("a1a2") is Termination.CONTINUE
        assert verifier.board.halfmove_clock == 0
        assert verifier.critical_plies == [1]

    def test_a_pawn_move_resets_the_clock(self):
        verifier = GameVerifier(chess.Board("6k1/5ppp/8/8/8/8/P7/R6K w - - 149 100"))
        assert verifier.push_uci("a2a3") is Termination.CONTINUE
        assert verifier.board.halfmove_clock == 0
        assert verifier.critical_plies == [1]


class TestFivefoldRepetition:
    SHUFFLE = "r3k3/8/8/8/8/8/8/R3K3 w - - 0 1"
    CYCLE = ["Rb1", "Rb8", "Ra1", "Ra8"]

    def test_fires_on_the_fifth_occurrence_not_the_fourth(self):
        start = chess.Board(self.SHUFFLE)
        start_key = repetition_key(start)
        verifier = GameVerifier(start)
        moves = moves_from_san(" ".join(self.CYCLE * 4), chess.Board(self.SHUFFLE))

        # Three full cycles bring the start position to four occurrences.
        for move in moves[:12]:
            assert verifier.push(move) is Termination.CONTINUE
        assert verifier.repetitions[start_key] == 4, "four is still legal"

        for move in moves[12:15]:
            assert verifier.push(move) is Termination.CONTINUE
        assert verifier.push(moves[15]) is Termination.FIVEFOLD_REPETITION
        assert verifier.repetitions[start_key] == 5
        assert verifier.plies == 16

    def test_the_starting_position_counts_as_one_occurrence(self):
        verifier = GameVerifier()
        assert verifier.repetitions[next(iter(verifier.repetitions))] == 1

    def test_constant_matches_the_rule(self):
        assert FIVEFOLD_REPETITION_COUNT == 5


class TestOtherTerminations:
    def test_checkmate(self):
        result = verify_game(moves_from_san("f3 e5 g4 Qh4"))
        assert result.termination is Termination.CHECKMATE
        assert result.plies == 4

    def test_stalemate(self):
        verifier = GameVerifier(chess.Board("7k/8/8/6Q1/8/8/8/K7 w - - 0 1"))
        assert verifier.push_uci("g5g6") is Termination.STALEMATE

    def test_insufficient_material(self):
        verifier = GameVerifier(chess.Board("7k/8/8/8/8/8/6K1/7r w - - 10 30"))
        assert verifier.push_uci("g2h1") is Termination.INSUFFICIENT_MATERIAL


class TestPriority:
    """Order matters wherever two conditions could fire on the same move."""

    def test_checkmate_beats_the_move_rule(self):
        assert (
            GameVerifier(chess.Board(BRINK)).push_uci("a1a8") is Termination.CHECKMATE
        )

    def test_checkmate_can_never_collide_with_fivefold(self):
        """Not a priority test -- a proof that the collision cannot arise.

        Checkmate is a function of placement and side to move, which are both
        part of the repetition key. So if a position is mate on its fifth
        occurrence it was mate on its first, and the game ended there. A mating
        position therefore always has a repetition count of exactly 1.
        """
        verifier = GameVerifier()
        for move in moves_from_san("f3 e5 g4 Qh4"):
            verifier.push(move)
        assert verifier.termination is Termination.CHECKMATE
        assert verifier.repetitions[repetition_key(verifier.board)] == 1

    def test_stalemate_beats_the_move_rule(self):
        verifier = GameVerifier(chess.Board("7k/8/8/6Q1/8/8/8/K7 w - - 149 90"))
        assert verifier.push_uci("g5g6") is Termination.STALEMATE


class TestErrors:
    def test_illegal_move_raises_with_context(self):
        verifier = GameVerifier()
        with pytest.raises(IllegalMove) as excinfo:
            verifier.push_uci("e2e5")
        assert excinfo.value.ply == 1
        assert "e2e5" in str(excinfo.value)

    def test_a_move_after_the_game_ended_raises(self):
        verifier = GameVerifier(chess.Board(BRINK))
        verifier.push_uci("a1a8")
        with pytest.raises(GameAlreadyOver):
            verifier.push_uci("h1g1")

    def test_verify_game_rejects_leftover_moves(self):
        moves = moves_from_san("f3 e5 g4 Qh4") + [chess.Move.from_uci("h1g1")]
        with pytest.raises(Exception, match="unplayed"):
            verify_game(moves)


class TestCriticalMoves:
    def test_counts_pawn_moves_and_captures(self):
        result = verify_game(moves_from_san("e4 d5 exd5 Qxd5 Nc3"))
        # e4, d5, exd5, Qxd5 are critical; Nc3 is not.
        assert result.critical_plies == (1, 2, 3, 4)

    def test_a_final_checkmate_closes_a_segment_even_when_quiet(self):
        """K in ``L = 150K - S - Σδ`` counts segments, and the mate ends one."""
        result = verify_game(moves_from_san("f3 e5 g4 Qh4"))
        assert result.termination is Termination.CHECKMATE
        assert result.critical_plies == (1, 2, 3), "Qh4# is neither pawn nor capture"
        assert result.critical_count == 4, "but it still closes the last segment"

    def test_a_final_checkmate_that_is_itself_critical_is_not_double_counted(self):
        """Scholar's mate ends on Qxf7#, which is a capture and so already a
        critical move. It must not be counted twice."""
        result = verify_game(moves_from_san("e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7"))
        assert result.termination is Termination.CHECKMATE
        assert result.critical_plies == (1, 2, 7)
        assert result.critical_plies[-1] == result.plies
        assert result.critical_count == 3

    @pytest.mark.parametrize(
        ("fen", "uci", "expected"),
        [
            ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "e5d6", True),  # en passant
            ("4k3/7P/8/8/8/8/8/4K3 w - - 0 1", "h7h8q", True),  # promotion
            ("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a2", False),  # quiet rook
        ],
    )
    def test_edge_cases(self, fen: str, uci: str, expected: bool):
        verifier = GameVerifier(chess.Board(fen))
        verifier.push_uci(uci)
        assert bool(verifier.critical_plies) is expected
