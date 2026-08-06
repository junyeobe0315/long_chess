"""Critical-segment representation of a game.

May import from ``long_chess.verifier``; the reverse is forbidden.
"""

from .compress import (
    cancel_cycles,
    compress,
    find_cross_segment_repeats,
    potential,
)
from .io import dump, from_dict, load, to_dict, to_pgn
from .segment import Segment, Skeleton, SplitError, split_game
from .stats import SEGMENT_TARGET, Phase, SkeletonStats, analyse

__all__ = [
    "SEGMENT_TARGET",
    "Phase",
    "Segment",
    "Skeleton",
    "SkeletonStats",
    "SplitError",
    "analyse",
    "cancel_cycles",
    "compress",
    "dump",
    "find_cross_segment_repeats",
    "from_dict",
    "load",
    "potential",
    "split_game",
    "to_dict",
    "to_pgn",
]
