"""The home-rank lemma's proof obligations.

The proof itself is in ``long_chess.bound.invariant``'s docstring. These
discharge the claims about the rules of chess that it appeals to.
"""

from __future__ import annotations

import pytest

from long_chess.bound import MAX_ATTACKER_PAWN_MOVES, verify
from long_chess.bound.invariant import (
    check_castling_stays_on_back_ranks,
    check_en_passant_victim_rank,
    check_initial_home_ranks,
)


@pytest.fixture(scope="module")
def obligations():
    """A small corpus: the exhaustive obligations do not depend on its
    size, and `certify.py` runs the full-size corpus into the certificate
    on every `make verify-full`."""
    return verify(games=6, plies=100)




def test_every_obligation_is_discharged(obligations):
    failed = [o for o in obligations if not o.discharged]
    assert failed == [], [o.describe() for o in failed]


def test_all_seven_are_present(obligations):
    assert [o.tag for o in obligations] == ["H0", "H1", "H2", "H3", "H4", "H5", "H6"]


class TestTheFiniteOnesAreActuallyExhausted:
    """H0, H3 and H4 have finitely many cases, so they are settled outright
    rather than sampled. The distinction is the whole difference between the
    proof and the seven million moves it replaces."""

    def test_the_initial_position(self):
        assert check_initial_home_ranks().method == "exhaustive"

    def test_castling(self):
        obligation = check_castling_stays_on_back_ranks()
        assert obligation.method == "exhaustive"
        assert obligation.discharged
        assert "ranks [1, 8]" in obligation.detail

    def test_en_passant(self):
        obligation = check_en_passant_victim_rank()
        assert obligation.method == "exhaustive"
        assert obligation.discharged
        assert "ranks [4, 5]" in obligation.detail


class TestTheCorpusOnesSawEnough:
    """H1, H2, H5 and H6 hold for every position there is, so no enumeration
    settles them — they come from the FIDE laws, and these check that the move
    generator agrees. A corpus that saw nothing would prove nothing."""

    @pytest.mark.parametrize("tag", ["H1", "H2", "H5", "H6"])
    def test_the_check_had_material_to_work_with(self, obligations, tag: str):
        obligation = next(o for o in obligations if o.tag == tag)
        assert "positions" in obligation.method
        assert obligation.cases > 1_000, f"{tag} only saw {obligation.cases} cases"

    def test_double_pushes_were_actually_observed(self, obligations):
        """H6 would pass vacuously if no double push ever occurred."""
        obligation = next(o for o in obligations if o.tag == "H6")
        assert "ranks [2, 7]" in obligation.detail


def test_the_conclusion_matches_the_model_constant():
    """Part 3 of the proof is what the model's FIRST_BLOCK_PAWN_LIMIT encodes."""
    from long_chess.bound import FIRST_BLOCK_PAWN_LIMIT

    assert MAX_ATTACKER_PAWN_MOVES == FIRST_BLOCK_PAWN_LIMIT == 4
