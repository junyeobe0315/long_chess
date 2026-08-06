"""Packing closed quiet walks into a skeleton's bridges.

May import from ``long_chess.verifier`` and ``long_chess.skeleton``.
"""

from .capacity import (
    MEASURE_LIMIT,
    CapacityFeatures,
    blocking_reason,
    estimate_capacity,
    features,
    has_closed_walk,
    is_packable,
    measure_capacity,
    measure_segment_capacity,
    position_occurrences,
    reversible_movers,
)
from .pad import (
    PadReport,
    SegmentPadStats,
    pack,
    pad_segment,
    pad_skeleton,
    plan_lengths,
    segment_rng,
)
from .targets import MAX_QUIET, padding_needed, quiet_target, segment_target
from .walks import (
    MAX_OCCURRENCES,
    WalkBudget,
    find_closed_walk,
    find_closed_walk_traced,
    find_four_ply_walk,
    find_six_ply_walk,
    find_walk_dfs,
    is_usable_position,
    quiet_moves,
)

__all__ = [
    "MAX_OCCURRENCES",
    "MEASURE_LIMIT",
    "CapacityFeatures",
    "MAX_QUIET",
    "PadReport",
    "SegmentPadStats",
    "WalkBudget",
    "blocking_reason",
    "estimate_capacity",
    "features",
    "find_closed_walk",
    "find_closed_walk_traced",
    "find_four_ply_walk",
    "find_six_ply_walk",
    "find_walk_dfs",
    "has_closed_walk",
    "is_packable",
    "is_usable_position",
    "measure_capacity",
    "measure_segment_capacity",
    "pack",
    "pad_segment",
    "pad_skeleton",
    "padding_needed",
    "plan_lengths",
    "position_occurrences",
    "quiet_moves",
    "quiet_target",
    "reversible_movers",
    "segment_rng",
    "segment_target",
]
