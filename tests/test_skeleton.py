"""Splitting a game into critical segments, and reading K/S/Σδ off the result."""

from __future__ import annotations

import chess
import pytest

from long_chess.skeleton import (
    Segment,
    Skeleton,
    SplitError,
    analyse,
    from_dict,
    split_game,
    to_dict,
)
from long_chess.verifier import moves_from_san

# Rooks free to shuffle on the a-file, and one pawn each so a critical move is
# always available.
START = "r3k3/p7/8/8/8/8/P7/R3K3 w - - 0 1"


def segment(bridge_uci: list[str], critical_uci: str = "a2a3") -> Segment:
    return Segment(
        start_fen=START,
        bridge_moves=tuple(chess.Move.from_uci(uci) for uci in bridge_uci),
        critical_move=chess.Move.from_uci(critical_uci),
    )


class TestSegment:
    def test_length_counts_the_critical_move(self):
        assert segment([]).length == 1
        assert segment(["a1b1", "a8b8"]).length == 3

    def test_actor_is_the_side_on_move_after_the_bridge(self):
        assert segment([]).actor is chess.WHITE
        assert segment(["a1b1"]).actor is chess.BLACK
        assert segment(["a1b1", "a8b8"]).actor is chess.WHITE

    def test_actor_follows_the_start_turn(self):
        black_to_move = Segment(
            start_fen="r3k3/p7/8/8/8/8/P7/R3K3 b - - 0 1",
            bridge_moves=(),
            critical_move=chess.Move.from_uci("a7a6"),
        )
        assert black_to_move.actor is chess.BLACK

    def test_moves_is_bridge_then_critical(self):
        seg = segment(["a1b1"])
        assert seg.moves == (*seg.bridge_moves, seg.critical_move)


class TestSplitGame:
    def test_each_critical_move_closes_a_segment(self):
        skeleton = split_game(moves_from_san("e4 d5 Nf3 Nc6 exd5 Qxd5"))
        # e4(1) d5(2) exd5(5) Qxd5(6) are critical; Nf3/Nc6 are bridge.
        assert [s.length for s in skeleton.segments] == [1, 1, 3, 1]
        assert skeleton.critical_count == 4
        assert skeleton.plies == 6

    def test_a_quiet_checkmate_closes_the_last_segment(self):
        skeleton = split_game(moves_from_san("f3 e5 g4 Qh4"))
        assert skeleton.ends_in_checkmate
        assert skeleton.critical_count == 4
        assert skeleton.segments[-1].critical_move == chess.Move.from_uci("d8h4")

    def test_a_game_that_neither_mates_nor_ends_critical_is_rejected(self):
        with pytest.raises(SplitError, match="unterminated"):
            split_game(moves_from_san("e4 e5 Nf3 Nc6"))

    def test_no_moves_is_rejected(self):
        with pytest.raises(SplitError, match="no moves"):
            split_game([])

    def test_moves_round_trip(self):
        moves = moves_from_san("e4 d5 Nf3 Nc6 exd5 Qxd5")
        assert list(split_game(moves).moves) == moves

    def test_critical_sans_are_readable(self):
        skeleton = split_game(moves_from_san("e4 d5 Nf3 Nc6 exd5 Qxd5"))
        assert skeleton.critical_sans() == ("e4", "d5", "exd5", "Qxd5")


class TestAnalyse:
    def build(self, actors: str) -> Skeleton:
        """A skeleton whose segments have the given actors, W or B.

        The positions are fictional -- analyse() only reads actors and lengths
        -- so this lets us test the S and phase logic directly.
        """
        segments = []
        for actor in actors:
            start_turn = "w" if actor == "W" else "b"
            segments.append(
                Segment(
                    start_fen=f"r3k3/p7/8/8/8/8/P7/R3K3 {start_turn} - - 0 1",
                    bridge_moves=(),
                    critical_move=chess.Move.from_uci("a2a3"),
                )
            )
        return Skeleton(tuple(segments), ends_in_checkmate=True)

    def test_the_opening_counts_as_following_a_black_critical_move(self):
        """White closing the first segment is already a switch."""
        assert analyse(self.build("W")).actor_switches == 1
        assert analyse(self.build("B")).actor_switches == 0

    def test_switches_are_counted_between_consecutive_segments(self):
        stats = analyse(self.build("BBWWBB"))
        assert stats.actor_switches == 2
        assert stats.switch_segments == (2, 4)

    def test_a_switch_lowers_that_segment_target_by_one(self):
        stats = analyse(self.build("BW"))
        assert stats.segment_targets == (150, 149)

    def test_phases_group_consecutive_segments(self):
        stats = analyse(self.build("BBWWWB"))
        assert [(p.actor_name, p.size) for p in stats.phases] == [
            ("B", 2),
            ("W", 3),
            ("B", 1),
        ]

    def test_achievable_plies_is_the_packed_length(self):
        stats = analyse(self.build("BBW"))
        assert stats.achievable_plies == 150 * 3 - 1

    def test_score_is_lexicographic(self):
        """K dominates S dominates slack. A weighted sum invites the mistake of
        trading a critical move (150 ply) for switches (1 ply each)."""
        better_k = analyse(self.build("BBB")).score
        fewer_switches = analyse(self.build("BW")).score
        assert better_k > fewer_switches


class TestSerialisation:
    def test_round_trip(self):
        original = split_game(moves_from_san("e4 d5 Nf3 Nc6 exd5 Qxd5"))
        restored = from_dict(to_dict(original))
        assert restored == original
        assert restored.moves == original.moves

    def test_version_is_checked(self):
        data = to_dict(split_game(moves_from_san("f3 e5 g4 Qh4")))
        data["version"] = 999
        with pytest.raises(ValueError, match="unsupported skeleton format"):
            from_dict(data)
