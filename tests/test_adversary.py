"""Adversarial tests on the home-rank lemma.

The optimality result rests on this lemma alone once the counting is done, so
it gets attacked rather than assumed. See docs/optimality.md. The expensive
artefacts — one strict-mode hunt and one exhaustive audit per colour — are
module-scoped fixtures shared by every assertion, and the full-size attack
lives in ``scripts/attack_lemma.py`` (seeded, reproduces exactly).
"""

from __future__ import annotations

import chess
import pytest

from long_chess.bound import FIRST_BLOCK_PAWN_LIMIT, attack, audit, hunt

COLOURS = [chess.WHITE, chess.BLACK]
IDS = ["white", "black"]


@pytest.fixture(scope="module", params=COLOURS, ids=IDS)
def hunted(request):
    """Strict mode: the defender quiet, defender pawns untouchable."""
    return hunt(
        request.param, attempts=10, plies=250, allow_pawn_captures=False, seed=3
    )


@pytest.fixture(scope="module", params=COLOURS, ids=IDS)
def audited(request):
    """Every legal attacker move at every position one set of rollouts visits."""
    return audit(request.param, attempts=8, plies=150, seed=5)


class TestTheSearchWorks:
    """Controls. A search that finds nothing proves nothing unless it can find
    something, so these run with the lemma's restriction lifted, where a pawn
    demonstrably can get through."""

    @pytest.mark.parametrize("attacker", COLOURS, ids=IDS)
    def test_a_pawn_gets_through_when_it_may_take_defender_pawns(self, attacker):
        result = hunt(
            attacker, attempts=20, plies=250, allow_pawn_captures=True, seed=3
        )
        assert result.reached_home_rank
        assert result.best_pawn_moves >= 6

    @pytest.mark.parametrize("attacker", COLOURS, ids=IDS)
    def test_the_search_actually_moves_pawns(self, attacker):
        result = attack(attacker, plies=120, strategy="focus")
        assert result.best_pawn_moves > 0


class TestTheLemmaHolds:
    def test_no_pawn_exceeds_four_moves(self, hunted):
        assert hunted.best_pawn_moves <= FIRST_BLOCK_PAWN_LIMIT

    def test_four_moves_is_reached_so_the_bound_is_tight(self, hunted):
        """Not conservative. If the real limit were three, the model would be
        sound but the constant wrong."""
        assert hunted.best_pawn_moves == FIRST_BLOCK_PAWN_LIMIT

    def test_no_pawn_reaches_the_defender_home_rank(self, hunted):
        assert not hunted.reached_home_rank

    def test_the_defender_home_rank_is_never_disturbed(self, hunted):
        """The invariant the lemma turns on: eight pawns that cannot move and
        cannot be taken stay exactly where they are, and nothing else can stand
        on those squares."""
        assert hunted.invariant_breaks == 0


class TestExhaustively:
    """Stronger than the rollouts: every legal attacker move at every position,
    not only the one played."""

    def test_no_legal_move_lands_a_pawn_on_the_home_rank(self, audited):
        assert audited.violations == []
        assert audited.positions > 300
        assert audited.moves_checked > 6_000

    def test_en_passant_never_becomes_available(self, audited):
        """The one rule that could put a pawn somewhere it did not walk to.
        It needs a double push, which is a pawn move, which the defender is not
        making — counted rather than assumed."""
        assert audited.en_passant_offers == 0
