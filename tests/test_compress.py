"""Cycle cancellation.

The unit tests below are the inverse of what the padder will do: insert a closed walk,
then check cancellation puts it back exactly. The gate at the bottom is the
real one — compressing the published 17,697-ply game must reproduce Tom 7's
289-ply skeleton move for move.
"""

from __future__ import annotations

import chess
import pytest

from long_chess.skeleton import (
    Segment,
    cancel_cycles,
    compress,
    find_cross_segment_repeats,
    potential,
)
from long_chess.verifier import verify_game

START = "r3k3/p7/8/8/8/8/P7/R3K3 w - - 0 1"
CRITICAL = "a2a3"

# Real work: the rooks walk outward and never revisit a position. Even length,
# so White is still on move for the critical pawn push.
BASE = ["a1b1", "a8b8", "b1c1", "b8c8"]


def build(bridge_uci: list[str]) -> Segment:
    """A segment, checked to be playable before the test uses it.

    Hand-written bridges are easy to get wrong -- an odd-length bridge leaves
    the wrong side on move and the critical move is not even legal. Validating
    here means a broken fixture fails as a fixture, not as a mystery.
    """
    seg = Segment(
        start_fen=START,
        bridge_moves=tuple(chess.Move.from_uci(uci) for uci in bridge_uci),
        critical_move=chess.Move.from_uci(CRITICAL),
    )
    board = seg.board_at_start()
    for move in seg.moves:
        assert move in board.legal_moves, f"bad fixture: {move.uci()} illegal"
        board.push(move)
    return seg


def bridge_uci(seg: Segment) -> list[str]:
    return [move.uci() for move in seg.bridge_moves]


def closed_walk(board: chess.Board) -> list[str]:
    """A 4-ply walk returning ``board`` to exactly where it started.

    Found rather than hardcoded, so a loop can be inserted at any anchor
    without hand-picking squares that happen to be free there.
    """
    for white in board.legal_moves:
        after_white = board.copy()
        after_white.push(white)
        for black in after_white.legal_moves:
            probe = after_white.copy()
            probe.push(black)
            back_white = chess.Move(white.to_square, white.from_square)
            if back_white not in probe.legal_moves:
                continue
            probe.push(back_white)
            back_black = chess.Move(black.to_square, black.from_square)
            if back_black not in probe.legal_moves:
                continue
            return [white.uci(), black.uci(), back_white.uci(), back_black.uci()]
    raise AssertionError("no closed 4-ply walk available")


def pad(base: list[str], anchor: int) -> list[str]:
    """``base`` with a closed walk spliced in after ``anchor`` moves."""
    board = chess.Board(START)
    for uci in base[:anchor]:
        board.push(chess.Move.from_uci(uci))
    return [*base[:anchor], *closed_walk(board), *base[anchor:]]


class TestCancelCycles:
    def test_a_bridge_with_no_repeat_is_untouched(self):
        original = build(BASE)
        assert cancel_cycles(original) == original

    def test_an_empty_bridge_is_untouched(self):
        assert cancel_cycles(build([])).bridge_moves == ()

    def test_a_loop_back_to_the_start_is_removed_entirely(self):
        assert bridge_uci(cancel_cycles(build(pad([], 0)))) == []

    def test_repeated_loops_are_all_removed(self):
        loop = closed_walk(chess.Board(START))
        assert bridge_uci(cancel_cycles(build(loop * 3))) == []

    @pytest.mark.parametrize("anchor", range(len(BASE) + 1))
    def test_a_loop_inserted_at_any_anchor_is_undone(self, anchor: int):
        """The exact inverse of what the padder will do."""
        padded = build(pad(BASE, anchor))
        assert len(padded.bridge_moves) == len(BASE) + 4
        assert bridge_uci(cancel_cycles(padded)) == BASE

    def test_nested_padding_is_undone(self):
        once = pad(BASE, 2)
        twice = pad(once, 4)  # a loop inside the loop
        assert bridge_uci(cancel_cycles(build(twice))) == BASE

    def test_the_result_is_still_playable(self):
        compressed = cancel_cycles(build(pad(BASE, 2)))
        board = compressed.board_at_start()
        for move in compressed.moves:
            assert move in board.legal_moves
            board.push(move)

    def test_cancellation_is_idempotent(self):
        once = cancel_cycles(build(pad(BASE, 1)))
        assert cancel_cycles(once) == once

    def test_the_actor_is_preserved(self):
        """A closed walk returns the same side to move, so it has even length.

        Cancellation therefore cannot change a bridge's parity, and so cannot
        change who plays the critical move. If it could, compressing a game
        would silently rewrite S.
        """
        original = build(BASE)
        for anchor in range(len(BASE) + 1):
            padded = build(pad(BASE, anchor))
            assert len(padded.bridge_moves) % 2 == len(BASE) % 2
            assert padded.actor is original.actor
            assert cancel_cycles(padded).actor is original.actor


class TestCrossSegmentIndependence:
    """See docs/segment-independence.md for the argument these check."""

    def test_the_full_game_never_repeats_a_position_across_segments(
        self, full_skeleton
    ):
        """The conclusion, checked directly over all 17,697 ply.

        If it ever fails, per-segment repetition counting is unsound and both
        cancellation and the padding are built on sand.
        """
        assert find_cross_segment_repeats(full_skeleton) == []

    def test_the_potential_starts_at_thirty_two_pieces_and_ninety_six_steps(self):
        """That 96 is the same 96 as in the 'at most 96 pawn moves' bound."""
        assert potential(chess.Board()) == (32, 96)

    def test_quiet_moves_leave_the_potential_alone(self, full_skeleton):
        board = chess.Board(full_skeleton.start_fen)
        for segment in full_skeleton.segments:
            before = potential(board)
            for move in segment.bridge_moves:
                board.push(move)
                assert potential(board) == before
            board.push(segment.critical_move)

    def test_every_critical_move_strictly_lowers_the_potential(self, full_skeleton):
        """Which is what makes two segments unable to share a position.

        The closing checkmate is exempt: it is a quiet move, and it closes the
        last segment only because the game ends there.
        """
        board = chess.Board(full_skeleton.start_fen)
        lowered = 0
        for index, segment in enumerate(full_skeleton.segments):
            for move in segment.bridge_moves:
                board.push(move)
            before = potential(board)
            board.push(segment.critical_move)
            if index < len(full_skeleton.segments) - 1:
                assert potential(board) < before
                lowered += 1
        assert lowered == 117

    @pytest.mark.parametrize(
        ("fen", "uci", "reason"),
        [
            ("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", "a2a3", "single push"),
            ("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", "a2a4", "double push"),
            ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q", "promotion"),
            ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "e5d6", "en passant"),
            ("4k3/8/8/8/8/8/r7/R3K3 w - - 0 1", "a1a2", "capture"),
        ],
    )
    def test_each_kind_of_critical_move_lowers_it(self, fen, uci, reason):
        board = chess.Board(fen)
        before = potential(board)
        board.push_uci(uci)
        assert potential(board) < before, reason


class TestTheKnownGame:
    """The skeleton gate."""

    def test_compression_reproduces_tom7s_skeleton_exactly(
        self, compressed_skeleton, reference_skeleton
    ):
        assert compressed_skeleton.moves == reference_skeleton.moves

    def test_the_skeleton_is_289_ply(self, compressed_skeleton):
        assert compressed_skeleton.plies == 289

    def test_the_critical_sequence_survives_compression(
        self, full_skeleton, compressed_skeleton
    ):
        """Cancellation may shorten bridges. It must never change which
        critical moves are played, in what order, or by whom."""
        assert compressed_skeleton.critical_sans() == full_skeleton.critical_sans()
        assert compressed_skeleton.actors == full_skeleton.actors
        assert compressed_skeleton.critical_count == full_skeleton.critical_count == 118

    def test_the_skeleton_is_a_legal_game_ending_in_mate(self, compressed_skeleton):
        result = verify_game(list(compressed_skeleton.moves))
        assert result.plies == 289
        assert result.termination.value == "checkmate"
        assert result.critical_count == 118

    def test_compression_is_idempotent(self, compressed_skeleton):
        assert compress(compressed_skeleton) == compressed_skeleton

    def test_the_reference_skeleton_is_itself_legal(self, reference_skeleton):
        result = verify_game(list(reference_skeleton.moves))
        assert result.plies == 289
        assert result.termination.value == "checkmate"
