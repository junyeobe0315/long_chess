"""Filler: targets, closed walks, and packing bridges out to length."""

from __future__ import annotations

import random
from collections import Counter

import chess
import pytest

from long_chess.filler import (
    MAX_OCCURRENCES,
    WalkBudget,
    blocking_reason,
    find_closed_walk,
    find_four_ply_walk,
    find_six_ply_walk,
    find_walk_dfs,
    is_usable_position,
    pad_segment,
    padding_needed,
    plan_lengths,
    quiet_moves,
    quiet_target,
    segment_target,
)
from long_chess.skeleton import Segment, analyse
from long_chess.verifier import repetition_key

ENDGAME = "r3k3/p7/8/8/8/8/P7/R3K3 w - - 0 1"


def empty_budget() -> WalkBudget:
    return WalkBudget(Counter())


class TestQuietTarget:
    @pytest.mark.parametrize(
        ("start_turn", "actor", "expected"),
        [
            (chess.WHITE, chess.BLACK, 149),  # actor unchanged -> odd bridge
            (chess.BLACK, chess.WHITE, 149),
            (chess.WHITE, chess.WHITE, 148),  # actor switched -> even bridge
            (chess.BLACK, chess.BLACK, 148),
        ],
    )
    def test_all_four_combinations(self, start_turn, actor, expected):
        assert quiet_target(start_turn, actor) == expected

    def test_a_switch_is_exactly_where_start_turn_equals_actor(self):
        """A segment starts with whoever did *not* just make a critical move,
        so the actor matching the start turn means the actor has changed."""
        assert quiet_target(chess.WHITE, chess.WHITE) == 148
        assert quiet_target(chess.WHITE, chess.BLACK) == 149

    def test_targets_on_the_real_skeleton(self, reference_skeleton):
        stats = analyse(reference_skeleton)
        for index, segment in enumerate(reference_skeleton.segments):
            expected = 148 if index in stats.switch_segments else 149
            assert segment_target(segment) == expected

    def test_padding_needed_is_always_even(self, reference_skeleton):
        """Closed walks are even, so an odd shortfall would be unfillable."""
        for segment in reference_skeleton.segments:
            assert padding_needed(segment) % 2 == 0


class TestPlanLengths:
    def test_an_exact_fit_is_offered(self):
        assert plan_lengths(4) == [4]
        assert plan_lengths(6) == [6]

    def test_a_remainder_of_two_is_never_proposed(self):
        """No sum of 4s and 6s makes 2, so leaving 2 strands the segment."""
        for remaining in range(4, 200, 2):
            for length in plan_lengths(remaining):
                assert remaining - length != 2

    def test_two_cannot_be_filled_at_all(self):
        assert plan_lengths(2) == []

    def test_multiples_of_four_prefer_four(self):
        assert plan_lengths(8)[0] == 4
        assert plan_lengths(100)[0] == 4

    def test_two_mod_four_prefers_six(self):
        """4-ply walks alone only build multiples of 4."""
        assert plan_lengths(10)[0] == 6
        assert plan_lengths(102)[0] == 6

    def test_greedily_taking_the_first_choice_always_terminates(self):
        for start in range(4, 300, 2):
            remaining = start
            while remaining:
                choices = plan_lengths(remaining)
                assert choices, f"stranded at {remaining} from {start}"
                remaining -= choices[0]
            assert remaining == 0


class TestQuietMoves:
    def test_pawn_moves_are_excluded(self):
        board = chess.Board()
        assert all(
            board.piece_at(m.from_square).piece_type != chess.PAWN
            for m in quiet_moves(board)
        )
        assert len(list(quiet_moves(board))) == 4, "only the four knight moves"

    def test_captures_are_excluded(self):
        board = chess.Board("4k3/8/8/8/8/8/r7/R3K3 w - - 0 1")
        assert chess.Move.from_uci("a1a2") not in list(quiet_moves(board))

    def test_castling_is_excluded(self):
        """Legal filler in principle -- it does not reset the clock -- but it
        changes castling rights irreversibly, so no walk through it can close."""
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        assert any(board.is_castling(m) for m in board.legal_moves)
        assert not any(board.is_castling(m) for m in quiet_moves(board))

    def test_checks_are_allowed(self):
        """The published game's filler gives check; only terminal positions
        are off limits."""
        board = chess.Board("7k/8/8/8/8/8/8/R6K w - - 0 1")
        checking = chess.Move.from_uci("a1a8")
        assert checking in list(quiet_moves(board))


class TestUsablePosition:
    def test_checkmate_is_not_usable(self):
        board = chess.Board("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
        board.push_uci("a1a8")
        assert not is_usable_position(board)

    def test_stalemate_is_not_usable(self):
        board = chess.Board("7k/8/8/6Q1/8/8/8/K7 w - - 0 1")
        board.push_uci("g5g6")
        assert not is_usable_position(board)


def assert_closed_and_quiet(board: chess.Board, walk: list[chess.Move]) -> None:
    start_key = repetition_key(board)
    probe = board.copy(stack=False)
    for move in walk:
        assert move in probe.legal_moves
        assert not probe.is_capture(move)
        assert probe.piece_at(move.from_square).piece_type != chess.PAWN
        assert not probe.is_castling(move)
        probe.push(move)
        assert is_usable_position(probe)
    assert repetition_key(probe) == start_key, "the walk must close"


class TestWalks:
    def test_four_ply_walk_from_the_starting_position(self):
        board = chess.Board()
        walk = find_four_ply_walk(board, empty_budget(), random.Random(0))
        assert walk is not None and len(walk) == 4
        assert_closed_and_quiet(chess.Board(), walk)

    def test_four_ply_walk_is_a_move_and_its_reverse_each_side(self):
        board = chess.Board()
        walk = find_four_ply_walk(board, empty_budget(), random.Random(0))
        a, b, a_back, b_back = walk
        assert (a_back.from_square, a_back.to_square) == (a.to_square, a.from_square)
        assert (b_back.from_square, b_back.to_square) == (b.to_square, b.from_square)

    def test_six_ply_walk(self):
        board = chess.Board(ENDGAME)
        walk = find_six_ply_walk(board, empty_budget(), random.Random(0))
        assert walk is not None and len(walk) == 6
        assert_closed_and_quiet(chess.Board(ENDGAME), walk)

    def test_six_ply_walk_is_two_three_cycles(self):
        board = chess.Board(ENDGAME)
        w1, b1, w2, b2, w3, b3 = find_six_ply_walk(
            board, empty_budget(), random.Random(0)
        )
        assert w2.from_square == w1.to_square and w3.to_square == w1.from_square
        assert b2.from_square == b1.to_square and b3.to_square == b1.from_square

    @pytest.mark.parametrize("length", [4, 10])
    def test_dfs_finds_walks_of_any_even_length(self, length: int):
        board = chess.Board(ENDGAME)
        walk = find_walk_dfs(board, length, empty_budget(), random.Random(0))
        assert walk is not None and len(walk) == length
        assert_closed_and_quiet(chess.Board(ENDGAME), walk)

    def test_odd_lengths_are_rejected(self):
        with pytest.raises(ValueError, match="even length"):
            find_closed_walk(chess.Board(), 5, empty_budget(), random.Random(0))

    def test_a_walk_is_refused_when_the_anchor_is_already_at_the_limit(self):
        board = chess.Board()
        budget = WalkBudget(Counter({repetition_key(board): MAX_OCCURRENCES}))
        assert find_four_ply_walk(board, budget, random.Random(0)) is None

    def test_a_walk_never_pushes_a_position_past_the_limit(self):
        board = chess.Board()
        counts: Counter = Counter()
        rng = random.Random(0)
        for _ in range(20):
            walk = find_closed_walk(board.copy(), 4, WalkBudget(counts), rng)
            if walk is None:
                break
            probe = board.copy()
            for move in walk:
                probe.push(move)
                counts[repetition_key(probe)] += 1
        assert max(counts.values()) <= MAX_OCCURRENCES


class TestPadSegment:
    def segment_from(self, skeleton, index: int) -> Segment:
        return skeleton.segments[index]

    @pytest.mark.parametrize("index", [0, 58, 109, 117])
    def test_padding_reaches_the_target(self, compressed_skeleton, index: int):
        segment = self.segment_from(compressed_skeleton, index)
        padded = pad_segment(segment, random.Random(1))
        assert padded is not None
        assert len(padded.bridge_moves) == segment_target(segment)

    def test_padding_preserves_the_actor(self, compressed_skeleton):
        """Closed walks are even, so they cannot flip who plays the critical
        move. If they could, packing a skeleton would silently change S."""
        for index in (0, 10, 59, 109):
            segment = self.segment_from(compressed_skeleton, index)
            padded = pad_segment(segment, random.Random(2))
            assert padded.actor is segment.actor

    def test_the_padded_segment_is_playable(self, compressed_skeleton):
        segment = self.segment_from(compressed_skeleton, 0)
        padded = pad_segment(segment, random.Random(3))
        board = padded.board_at_start()
        for move in padded.moves:
            assert move in board.legal_moves
            board.push(move)

    def test_padding_keeps_the_critical_move(self, compressed_skeleton):
        segment = self.segment_from(compressed_skeleton, 0)
        padded = pad_segment(segment, random.Random(4))
        assert padded.critical_move == segment.critical_move
        assert padded.start_fen == segment.start_fen

    def test_a_full_segment_is_left_alone(self, compressed_skeleton):
        segment = self.segment_from(compressed_skeleton, 0)
        padded = pad_segment(segment, random.Random(5))
        assert pad_segment(padded, random.Random(6)) == padded

    def test_an_over_long_bridge_is_rejected(self, compressed_skeleton):
        segment = self.segment_from(compressed_skeleton, 0)
        padded = pad_segment(segment, random.Random(7))
        with pytest.raises(ValueError, match="over the target"):
            pad_segment(padded, random.Random(8), target=10)

    def test_a_parity_mismatch_is_rejected(self, compressed_skeleton):
        segment = self.segment_from(compressed_skeleton, 0)
        with pytest.raises(ValueError, match="parity"):
            pad_segment(segment, random.Random(9), target=segment_target(segment) - 1)





class TestKnownBlockedStartPositions:
    """Three segment starts admit no closed walk on their own; one bridge ply
    clears each. Pinned because the three causes — castling rights, check —
    are the ones anything packing an unfamiliar skeleton will meet."""

    @pytest.mark.parametrize(
        ("index", "expected"),
        [(6, "castling"), (88, "check"), (100, "check")],
    )
    def test_the_reason_is_still_reported(
        self, compressed_skeleton, index: int, expected: str
    ):
        reason = blocking_reason(compressed_skeleton.segments[index].board_at_start())
        assert reason is not None
        assert expected in reason


