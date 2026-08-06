"""Packing a bridge out to its target length with closed walks.

Backtracking with random restarts, not greedy insertion. When the packer gets
stuck it is rarely the current spot that is at fault — it is a loop chosen
earlier that used up a position's four occurrences. Unwinding one step tends to
land in the same dead end, so the segment is thrown away and retried from a
fresh seed.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

import chess

from ..skeleton import Segment, Skeleton
from ..verifier import RepetitionKey, repetition_key
from .targets import segment_target
from .walks import WalkBudget, find_closed_walk_traced

WALK_LENGTHS = (4, 6, 8, 10)
"""Shapes the packer will try, cheapest first."""


def plan_lengths(remaining: int) -> list[int]:
    """Walk lengths worth trying when ``remaining`` ply are still needed.

    Two rules. A walk must not overshoot, and it must not leave a remainder of
    2 — no combination of 4s and 6s makes 2, so landing there strands the
    segment.

    Beyond that, prefer lengths that leave a multiple of 4, since 4-ply walks
    are much cheaper to find than anything else. A bridge needing 10 more ply
    therefore takes a 6 first and then a 4, rather than a 4 first and getting
    stuck needing 6 twice.
    """
    candidates = [
        length
        for length in WALK_LENGTHS
        if length == remaining or remaining - length >= 4
    ]
    return sorted(
        candidates, key=lambda length: ((remaining - length) % 4 != 0, length)
    )


@dataclass
class _Bridge:
    """A bridge under construction, with its positions and repetition counts."""

    moves: list[chess.Move]
    positions: list[chess.Board]
    counts: Counter[RepetitionKey] = field(default_factory=Counter)

    @classmethod
    def build(cls, board: chess.Board, moves: Sequence[chess.Move] = ()) -> _Bridge:
        board = board.copy(stack=False)
        positions = [board.copy(stack=False)]
        for move in moves:
            board.push(move)
            positions.append(board.copy(stack=False))
        counts = Counter(repetition_key(position) for position in positions)
        return cls(list(moves), positions, counts)

    def insert(self, anchor: int, walk: list[chess.Move]) -> None:
        """Splice a closed walk in after ``anchor`` moves.

        The walk returns to where it started, so every position after the
        anchor is untouched. Only the walk's own positions are new — that is
        what makes this cheap enough to do forty times a segment.
        """
        board = self.positions[anchor].copy(stack=False)
        added: list[chess.Board] = []
        for move in walk:
            board.push(move)
            added.append(board.copy(stack=False))

        self.moves[anchor:anchor] = walk
        self.positions[anchor + 1 : anchor + 1] = added
        for position in added:
            self.counts[repetition_key(position)] += 1


@dataclass
class SegmentPadStats:
    """What the packer had to do to fill one segment.

    Collected because a segment that succeeds easily and one that only just
    succeeds look identical in the output. The difference shows up here:
    anchors tried per insertion, and how often the shaped enumerators failed
    and the DFS had to take over.
    """

    insertions: int = 0
    anchors_tried: int = 0
    by_method: Counter[str] = field(default_factory=Counter)
    by_length: Counter[int] = field(default_factory=Counter)

    @property
    def anchors_per_insertion(self) -> float:
        """1.0 means the first anchor tried always worked."""
        return self.anchors_tried / self.insertions if self.insertions else 0.0

    @property
    def dfs_fallbacks(self) -> int:
        return self.by_method["dfs"]


def pack(
    board: chess.Board,
    target: int,
    rng: random.Random,
    *,
    initial: Sequence[chess.Move] = (),
    stats: SegmentPadStats | None = None,
    best_effort: bool = False,
) -> list[chess.Move] | None:
    """Grow ``initial`` to ``target`` ply by splicing in closed walks.

    Returns None when it gets stuck, unless ``best_effort``, in which case it
    returns however far it got. Best effort is for *measuring* how much a
    position can hold; packing a real segment wants all or nothing, since a
    half-filled segment is slack and slack is lost ply.
    """
    bridge = _Bridge.build(board, initial)

    while len(bridge.moves) < target:
        remaining = target - len(bridge.moves)
        budget = WalkBudget(bridge.counts)
        if not _insert_somewhere(bridge, remaining, budget, rng, stats):
            return bridge.moves if best_effort else None

    return bridge.moves


def pad_segment(
    segment: Segment,
    rng: random.Random,
    *,
    target: int | None = None,
    stats: SegmentPadStats | None = None,
) -> Segment | None:
    """Fill one segment's bridge to its target, or give up.

    Returns None when no walk fits anywhere, which is the caller's cue to
    restart with a different seed rather than to try harder here.
    """
    target = segment_target(segment) if target is None else target
    if len(segment.bridge_moves) > target:
        raise ValueError(
            f"bridge is already {len(segment.bridge_moves)} ply, over the "
            f"target of {target}"
        )
    if (target - len(segment.bridge_moves)) % 2:
        raise ValueError(
            "bridge and target disagree in parity; a closed walk cannot fix "
            "that, so the segment's actor is not what its bridge implies"
        )

    moves = pack(
        segment.board_at_start(),
        target,
        rng,
        initial=segment.bridge_moves,
        stats=stats,
    )
    return None if moves is None else segment.with_bridge(moves)


def _insert_somewhere(
    bridge: _Bridge,
    remaining: int,
    budget: WalkBudget,
    rng: random.Random,
    stats: SegmentPadStats | None = None,
) -> bool:
    """Try every shape at every anchor until one walk fits."""
    anchors = list(range(len(bridge.positions)))
    rng.shuffle(anchors)

    for length in plan_lengths(remaining):
        for anchor in anchors:
            board = bridge.positions[anchor].copy(stack=False)
            walk, method = find_closed_walk_traced(board, length, budget, rng)
            if stats is not None:
                stats.anchors_tried += 1
            if walk is not None:
                bridge.insert(anchor, walk)
                if stats is not None:
                    stats.insertions += 1
                    stats.by_method[method] += 1
                    stats.by_length[length] += 1
                return True
    return False


@dataclass(frozen=True, slots=True)
class PadReport:
    """What it took to fill a skeleton."""

    attempts: tuple[int, ...]
    """Restarts per segment, one entry each. 1 means it worked first time."""

    failures: tuple[int, ...]
    """Segments that never filled, after every restart."""

    stats: tuple[SegmentPadStats, ...] = ()
    """Per-segment effort, when collection was asked for."""

    @property
    def total_attempts(self) -> int:
        return sum(self.attempts)


def segment_rng(seed: int, index: int, restart: int) -> random.Random:
    """The generator for one segment of one run.

    Derived from the three coordinates rather than drawn from a single stream,
    so a segment's filler depends only on ``(seed, index, restart)``. That
    keeps runs reproducible even when segments are packed out of order or in
    parallel, which the batch generator does.
    """
    return random.Random(f"{seed}:{index}:{restart}")


def pad_skeleton(
    skeleton: Skeleton,
    seed: int = 0,
    *,
    max_restarts: int = 8,
    collect_stats: bool = False,
) -> tuple[Skeleton, PadReport]:
    """Fill every segment of a skeleton to its target.

    Segments are independent — no position recurs across them — so each is
    packed on its own and one segment's restarts cost the others nothing.
    """
    padded: list[Segment] = []
    attempts: list[int] = []
    failures: list[int] = []
    all_stats: list[SegmentPadStats] = []

    for index, segment in enumerate(skeleton.segments):
        result = None
        used = 0
        stats = SegmentPadStats() if collect_stats else None
        for restart in range(max_restarts):
            used = restart + 1
            result = pad_segment(
                segment, segment_rng(seed, index, restart), stats=stats
            )
            if result is not None:
                break
        attempts.append(used)
        if stats is not None:
            all_stats.append(stats)
        if result is None:
            failures.append(index)
            padded.append(segment)
        else:
            padded.append(result)

    return (
        Skeleton(tuple(padded), ends_in_checkmate=skeleton.ends_in_checkmate),
        PadReport(tuple(attempts), tuple(failures), tuple(all_stats)),
    )
