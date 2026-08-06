"""S ≥ 3, by direct counting. This is the source of truth for the final bound.

Critical events fall into maximal single-colour runs — *blocks* — and the block
sequence fixes `S`, the number of times the colour making critical moves
changes. Counting the virtual Black critical move before ply 1, an alternating
sequence of `n` blocks has `S = n − 1` if it opens with Black and `S = n` if it
opens with White, so `S ≤ 2` leaves exactly five shapes:

    B        W        B W        W B        B W B

A sixth case is vacuous and worth one line: a game with no critical moves at
all has an *empty* actor sequence and none of these shapes — and it cannot
have `K = 118`, which needs at least 117 critical moves, so the five non-empty
shapes are exhaustive everywhere the refutations run.

Every one of them is refuted here, from `K = 118` and the two lemmas in
:mod:`long_chess.bound.pawns` and :mod:`long_chess.bound.invariant`. No solver
is involved. :mod:`long_chess.model` decides the same question with CP-SAT and
again with arithmetic, and those are cross-checks on this — not the proof.

.. rubric:: Which sequence the five shapes are shapes *of*

`K` counts segment endpoints, and the last of them may be the **terminal quiet
segment** rather than a critical move — a quiet mate, or the moves that run out
the 75-move or repetition clock. So the endpoint sequence `S` is measured over
is not quite the critical-move actor sequence: it may carry one extra endpoint
at the end.

The refutations below are all statements about **critical** moves — who
captures what, and when a pawn may move. They need the critical-move actor
sequence to be one of the five, and that follows in one step:

    Deleting the optional terminal endpoint cannot increase the number of actor
    switches. So if the whole game has S ≤ 2, its critical-move actor sequence
    has S ≤ 2 too, and is therefore one of the same five shapes.

Deleting it either leaves the shape alone — when its block holds critical moves
as well — or removes the last block entirely, and an alternating sequence one
block shorter has exactly one switch fewer. :func:`check_terminal_endpoint_free`
exhausts that over every shape up to twelve blocks rather than leaving it as a
remark, because it is exactly the boundary an outside reader will ask about.

The refutations all start from the same place. `K = 118` forces
`P = 96` (:func:`~long_chess.bound.pawns.equality_conditions`), which means
**every one of the sixteen pawns makes exactly six moves and promotes**, and
`C + T = 30` with `T ≤ 1`, so `C ≥ 29`. Those two facts do all the work.

.. rubric:: Units, not pieces

The counting is over **units** — the 32 things that start on the board, each
followed through the whole game — not over piece types. A unit that began as a
pawn stays that unit after promoting, and "only seven of a side's capturable
units did not start as pawns" is a statement about origins. It matters here
because `P = 96` promotes every pawn, so a pawn-origin unit captured later in
the game is captured as a queen; the argument still counts it against the eight
pawn origins, which is what makes ``≥ 14 − 7 = 7`` correct.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pawns import (
    FILES,
    FIRST_BLOCK_PAWN_LIMIT,
    MAX_CAPTURES_PLUS_CLOSING,
    MAX_CLOSING_SEGMENT,
    MAX_CRITICAL_SEGMENTS,
    MAX_PAWN_MOVES,
    PAWN_STEPS,
    equality_conditions,
)

NON_PAWNS = 7
"""Capturable non-king pieces a side has: two rooks, two knights, two bishops,
a queen. The king cannot be captured."""

PAWNS = FILES
CAPTURABLE_PER_SIDE = PAWNS + NON_PAWNS  # 15

SEGMENT_TARGET = 150
"""Ply a critical segment can hold: 149 reversible plus the critical move."""


def switches(colours: tuple[str, ...]) -> int:
    """`S` for a block sequence, counting the virtual Black move before ply 1.

    A leading Black block is free — the game opens as if Black had just made a
    critical move — and a leading White block costs one immediately.
    """
    if not colours:
        return 0
    return len(colours) - 1 if colours[0] == "B" else len(colours)


def alternating_shapes(max_blocks: int) -> list[tuple[str, ...]]:
    """Every alternating block sequence of up to ``max_blocks`` blocks.

    Blocks are *maximal* single-colour runs, so consecutive blocks differ in
    colour and the sequence is determined by its first colour and its length.
    """
    shapes = []
    for length in range(1, max_blocks + 1):
        for first in ("B", "W"):
            other = "W" if first == "B" else "B"
            shapes.append(
                tuple(first if index % 2 == 0 else other for index in range(length))
            )
    return shapes


def shapes_with_at_most(limit: int, *, search_depth: int = 8) -> list[tuple[str, ...]]:
    """Every block shape with ``S ≤ limit``, and the list is complete.

    Completeness is not a search result. `S` grows by one with each extra block
    — `S = n − 1` opening with Black, `S = n` opening with White — so no shape
    longer than ``limit + 1`` blocks can qualify, and ``search_depth`` only has
    to exceed that. It is enumerated anyway rather than reasoned about in a
    comment, and :func:`shapes_with_at_most` is asserted complete in the tests.
    """
    if search_depth <= limit + 1:
        raise ValueError("search depth must exceed limit + 1 for the list to close")
    return [
        colours
        for colours in alternating_shapes(search_depth)
        if switches(colours) <= limit
    ]


def critical_actor_shape(
    colours: tuple[str, ...], *, terminal_alone: bool
) -> tuple[str, ...]:
    """The shape of the **critical-move** actors alone.

    `K`'s last endpoint may be a terminal quiet segment rather than a critical
    move. When that segment is the only thing in its block, dropping it drops
    the block; otherwise the block has critical moves of its own and the shape
    is unchanged.
    """
    return colours[:-1] if terminal_alone and colours else colours


@dataclass(frozen=True, slots=True)
class TerminalEndpointCheck:
    """Whether dropping the terminal endpoint can ever add an actor switch."""

    shapes_checked: int
    worst_increase: int
    """Maximum of ``S(critical) − S(whole)``. Must be ``≤ 0``."""

    @property
    def free(self) -> bool:
        return self.worst_increase <= 0


def check_terminal_endpoint_free(max_blocks: int = 12) -> TerminalEndpointCheck:
    """Exhaust the claim that the terminal endpoint never costs a switch.

    The refutations in this module are statements about *critical* moves, while
    `S` is measured over all `K` endpoints — one of which may be a terminal
    quiet segment. They line up because dropping that endpoint cannot increase
    the switch count, so a game with `S ≤ 2` overall has a critical-move actor
    sequence with `S ≤ 2`, which is one of the same five shapes.

    Checked over both readings of every alternating shape rather than argued,
    since it is the seam between two definitions and seams are where reviewers
    look first.
    """
    increases = [
        switches(critical_actor_shape(colours, terminal_alone=alone))
        - switches(colours)
        for colours in alternating_shapes(max_blocks)
        for alone in (False, True)
    ]
    return TerminalEndpointCheck(
        shapes_checked=len(increases),
        worst_increase=max(increases) if increases else 0,
    )


@dataclass(frozen=True, slots=True)
class Refutation:
    """One block shape, and why `K = 118` cannot be scheduled into it.

    All five refutations come out at the same place — the shape cannot fit the
    96 pawn moves `K = 118` demands — so the verdict is **derived** from the two
    numbers rather than stated alongside them. Stating it separately is how a
    constant could drift until the argument no longer closed while the code went
    on reporting IMPOSSIBLE, which is the failure this whole file exists to
    avoid making.
    """

    colours: tuple[str, ...]
    switches: int
    pawn_moves_available: int
    """The most pawn moves this shape permits, given what the counting forces."""

    pawn_moves_required: int
    """What `K = 118` demands: 96."""

    ground: str
    """The load-bearing step: ``counting`` or ``home-rank lemma``."""

    detail: str

    @property
    def refuted(self) -> bool:
        return self.pawn_moves_available < self.pawn_moves_required

    @property
    def shortfall(self) -> int:
        return max(0, self.pawn_moves_required - self.pawn_moves_available)

    @property
    def name(self) -> str:
        return " ".join(self.colours)

    def describe(self) -> str:
        verdict = "IMPOSSIBLE" if self.refuted else "not refuted"
        return (
            f"{self.name:8s} S={self.switches}  {verdict} ({self.ground})\n"
            f"    {self.detail}"
        )


REFUTABLE_SWITCHES = 2
"""The largest `S` this module refutes. Raising it needs new arguments, not a
bigger enumeration: `S = 3` is attained by the published game."""


def minimum_captures() -> int:
    """`C ≥ 29`, from `C + T = 30` and `T ≤ 1`."""
    return MAX_CAPTURES_PLUS_CLOSING - MAX_CLOSING_SEGMENT


def _other(colour: str) -> str:
    return "B" if colour == "W" else "W"


def _refute_single_block(colours: tuple[str, ...]) -> Refutation:
    """One block: only one colour ever makes a critical move.

    `K = 118` forces every pawn on the board to move, a pawn move is a critical
    move of that pawn's own colour, and pawns come in two colours.
    """
    equality = equality_conditions()
    colour = colours[0]
    # Only one colour has a block, so only that colour's eight pawns can move
    # at all — half the board's pawn moves are unreachable before anything else
    # is considered.
    available = PAWNS * PAWN_STEPS
    return Refutation(
        colours=colours,
        switches=switches(colours),
        pawn_moves_available=available,
        pawn_moves_required=equality.pawn_moves,
        ground="counting",
        detail=(
            f"K = {MAX_CRITICAL_SEGMENTS} forces P = {equality.pawn_moves}, so all "
            f"{2 * PAWNS} pawns move {equality.moves_per_pawn} times each. A pawn "
            f"move is a critical move of its own colour, and this shape gives "
            f"{_other(colour)} no block to make one in, so only {colour}'s "
            f"{PAWNS} pawns can move: P ≤ {available}"
        ),
    )


def _refute_two_blocks(colours: tuple[str, ...]) -> Refutation:
    """Two blocks: everything one colour does, then everything the other does.

    Both orderings die to the same count, and it is not close. Write the shape
    as (X, Y), so every X critical event precedes every Y critical event.

    `C ≥ 29`, and Y can capture at most the 15 capturable X pieces, so **X makes
    at least 14 captures**. Every one of them is an X critical event, hence in
    block 1, hence before Y has made a single critical move — so each victim
    made none of its own. Y has only 7 capturable non-pawns, so at least
    ``14 − 7 = 7`` of the victims are Y pawns that never moved, and at least
    ``7 × 6 = 42`` pawn moves are gone against a P that has to be exactly 96.
    """
    equality = equality_conditions()
    first, second = colours
    by_first = minimum_captures() - CAPTURABLE_PER_SIDE
    pawn_victims = by_first - NON_PAWNS
    lost = pawn_victims * PAWN_STEPS
    reachable = equality.pawn_moves - lost
    return Refutation(
        colours=colours,
        switches=switches(colours),
        pawn_moves_available=reachable,
        pawn_moves_required=equality.pawn_moves,
        ground="counting",
        detail=(
            f"C ≥ {minimum_captures()} and {second} can take at most "
            f"{CAPTURABLE_PER_SIDE} units, so {first} makes ≥{by_first} captures — "
            f"all in block 1, before {second} has made any critical move. Only "
            f"{NON_PAWNS} of {second}'s units did not start as pawns, so "
            f"≥{pawn_victims} pawn-origin {second} units are taken having made "
            f"no pawn move, costing ≥{lost} pawn moves: P ≤ {reachable} against "
            f"the {equality.pawn_moves} that K = {MAX_CRITICAL_SEGMENTS} demands"
        ),
    )


def _refute_black_white_black() -> Refutation:
    """B, W, B. The one shape counting alone does not kill.

    White's critical events are all in the middle block. `C ≥ 29` and Black can
    take at most the 15 capturable White pieces, so **White makes at least 14
    captures**, all in that middle block. Black has only 7 capturable non-pawns,
    so at least 7 of White's victims are Black pawns, taken in the middle block.

    `P = 96` gives each of those Black pawns six moves, and a piece moves before
    it is taken, so all six fall in the first block. Two things are then true of
    the first block:

    - White has made no critical move in it — it is a Black block — so every
      White move in it is quiet;
    - no White pawn has been captured in it either. A White pawn's six moves can
      only fall in the middle block, so a White pawn taken in the first block
      makes none, and `P = 96` has no six moves to give up.

    Those are exactly the hypotheses of the home-rank lemma
    (:mod:`long_chess.bound.invariant`), which caps a Black pawn at four moves
    while White's home rank is intact. Seven pawns needing six apiece and
    allowed four is a contradiction — and this is the only shape whose
    refutation needs the lemma at all.
    """
    equality = equality_conditions()
    by_white = minimum_captures() - CAPTURABLE_PER_SIDE
    pawn_victims = by_white - NON_PAWNS
    per_pawn = PAWN_STEPS - FIRST_BLOCK_PAWN_LIMIT
    lost = pawn_victims * per_pawn
    reachable = equality.pawn_moves - lost
    return Refutation(
        colours=("B", "W", "B"),
        switches=switches(("B", "W", "B")),
        pawn_moves_available=reachable,
        pawn_moves_required=equality.pawn_moves,
        ground="home-rank lemma",
        detail=(
            f"C ≥ {minimum_captures()} forces White to make ≥{by_white} captures, "
            f"all in the middle block, so ≥{pawn_victims} pawn-origin Black units "
            f"die there and must finish their {PAWN_STEPS} pawn moves in block 1. "
            f"In block 1 White makes no critical move and loses no pawn (a White "
            f"pawn taken there would make none of its {PAWN_STEPS}), so White's "
            f"home rank is intact and the lemma caps a Black pawn at "
            f"{FIRST_BLOCK_PAWN_LIMIT}. Each of the {pawn_victims} is {per_pawn} "
            f"short: P ≤ {reachable} against {equality.pawn_moves}"
        ),
    )


def refute(colours: tuple[str, ...]) -> Refutation:
    """Refute one `S ≤ 2` shape, or say plainly that this module does not.

    A shape with `S ≥ 3` comes back **not refuted**, with the full 96 pawn moves
    available — which for `B W B W` is simply true, and is why the answer is 3
    rather than something larger.
    """
    if switches(colours) > REFUTABLE_SWITCHES:
        return Refutation(
            colours=colours,
            switches=switches(colours),
            pawn_moves_available=MAX_PAWN_MOVES,
            pawn_moves_required=MAX_PAWN_MOVES,
            ground="none needed",
            detail="S ≥ 3 already; nothing to refute",
        )
    if len(colours) == 1:
        return _refute_single_block(colours)
    if len(colours) == 2:
        return _refute_two_blocks(colours)
    if colours == ("B", "W", "B"):
        return _refute_black_white_black()
    raise AssertionError(f"unhandled S ≤ 2 shape {colours}")


def refutations(limit: int = REFUTABLE_SWITCHES) -> list[Refutation]:
    """Every shape with ``S ≤ limit``, and what becomes of it."""
    return [refute(colours) for colours in shapes_with_at_most(limit)]


@dataclass(frozen=True, slots=True)
class SwitchBound:
    """`S ≥ 3` **for games with `K = 118`**, and the ply bound that follows.

    The conditionality is the whole content of the class. Every refutation in
    this module starts from `P = 96` and `C ≥ 29`, and both come from `K = 118`
    — so none of them says anything about a game with fewer critical segments,
    and `S ≥ 3` is emphatically *not* a global fact. See
    :func:`ply_bound` for the case analysis that turns it into one about `L`.
    """

    minimum_switches: int
    critical_segments: int
    refuted_shapes: tuple[Refutation, ...]

    @property
    def max_plies(self) -> int:
        """`150K − S` for this `K` alone. Not the bound on all games."""
        return SEGMENT_TARGET * self.critical_segments - self.minimum_switches

    def describe(self) -> str:
        return (
            f"at K = {self.critical_segments}, every S ≤ "
            f"{self.minimum_switches - 1} shape is refuted, so S ≥ "
            f"{self.minimum_switches} and L ≤ {SEGMENT_TARGET}·"
            f"{self.critical_segments} − {self.minimum_switches} = "
            f"{self.max_plies:,}"
        )


def switch_lower_bound(*, limit: int = REFUTABLE_SWITCHES) -> SwitchBound:
    """`S ≥ limit + 1` for games with `K = 118`, and only for those.

    Raises rather than returns a weaker bound when a shape survives: a shape
    left standing is the whole result gone, and reporting it as a smaller number
    would let it pass as a tightening.

    .. rubric:: There is no ``critical_segments`` argument, on purpose

    There used to be, defaulting to 118, and it was a trap: every refutation
    below uses `P = 96` and `C ≥ 29` regardless, so ``switch_lower_bound(117)``
    returned `S ≥ 3` while having proved nothing of the sort. `S ≥ 3` is false
    in general —

        1. Nf3 Nf6  2. Ng1 Ng8   (×4)

    is a legal 16-ply game ending in fivefold repetition with no pawn move and
    no capture, so `K = 1`, and its single endpoint is a Black move against the
    virtual Black opening, so `S = 0`. Pinned in
    ``tests/test_bound.py::TestSwitchThreeIsNotGlobal``.

    Games with smaller `K` are handled by :func:`ply_bound`, which does not need
    a switch bound for them at all.
    """
    terminal = check_terminal_endpoint_free()
    if not terminal.free:
        raise ValueError(
            "dropping the terminal endpoint can add an actor switch, so the "
            "refutations below are not about the sequence S is measured over"
        )
    found = refutations(limit)
    surviving = [r.name for r in found if not r.refuted]
    if surviving:
        raise ValueError(f"shapes with S ≤ {limit} not refuted: {surviving}")
    return SwitchBound(
        minimum_switches=limit + 1,
        critical_segments=MAX_CRITICAL_SEGMENTS,
        refuted_shapes=tuple(found),
    )


@dataclass(frozen=True, slots=True)
class PlyBound:
    """`L ≤ 17,697`, by cases on `K`. The theorem, in the form it is true in."""

    max_critical_segments: int
    """`K ≤ 118`, from :func:`~long_chess.bound.pawns.critical_bound`."""

    minimum_switches_at_max: int
    """`S ≥ 3`, but only when `K` is at its maximum."""

    @property
    def at_max_k(self) -> int:
        """`150·118 − 3`. The binding case."""
        return (
            SEGMENT_TARGET * self.max_critical_segments - self.minimum_switches_at_max
        )

    @property
    def below_max_k(self) -> int:
        """`150·117`, using only `S ≥ 0`. No switch argument is needed here —
        one whole segment is worth more than every switch a game could have."""
        return SEGMENT_TARGET * (self.max_critical_segments - 1)

    @property
    def max_plies(self) -> int:
        return max(self.at_max_k, self.below_max_k)

    @property
    def binding_case(self) -> str:
        return "K = 118" if self.at_max_k >= self.below_max_k else "K ≤ 117"

    def describe(self) -> str:
        lines = (
            f"K ≤ {self.max_critical_segments}, and",
            f"  K ≤ {self.max_critical_segments - 1}:  L ≤ {SEGMENT_TARGET}·"
            f"{self.max_critical_segments - 1} = {self.below_max_k:,}"
            "   (S ≥ 0 is enough)",
            f"  K = {self.max_critical_segments}:  S ≥ "
            f"{self.minimum_switches_at_max}, so L ≤ {SEGMENT_TARGET}·"
            f"{self.max_critical_segments} − {self.minimum_switches_at_max} = "
            f"{self.at_max_k:,}",
            f"  therefore L ≤ {self.max_plies:,}, attained in the "
            f"{self.binding_case} case",
        )
        return "\n".join(lines)


def ply_bound() -> PlyBound:
    """`L ≤ 17,697`, stated the way it is actually true.

    `L ≤ 150K − S` needs a lower bound on `S` only where `K` is large enough for
    it to matter, and it matters in exactly one place:

    - `K ≤ 117` gives `L ≤ 150·117 = 17,550` from `S ≥ 0` alone. Giving up a
      whole critical segment costs 150 ply, and no game has 150 switches to save
      against that.
    - `K = 118` is the only case left, and there :func:`switch_lower_bound`
      gives `S ≥ 3`, so `L ≤ 150·118 − 3 = 17,697`.

    `17,697 > 17,550`, so the second case is binding and the bound is 17,697.

    Writing it as two cases is not pedantry — `S ≥ 3` is false for small `K`,
    and a bound quoted as "`K ≤ 118` and `S ≥ 3`" claims a fact about every
    legal game that this project has not proved and that is not true.
    """
    return PlyBound(
        max_critical_segments=MAX_CRITICAL_SEGMENTS,
        minimum_switches_at_max=switch_lower_bound().minimum_switches,
    )
