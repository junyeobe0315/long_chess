"""Shared fixtures.

The expensive artefacts are session-scoped so the suite pays for each once,
and the parsed reference game is additionally cached across runs in pytest's
own cache, keyed by the PGN's SHA-256 — pure data, so the cache can never go
stale against code changes; a changed file changes the key.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

DATA = Path(__file__).parent.parent / "data"
REFERENCE_PGN = DATA / "longest.pgn"
REFERENCE_SKELETON = DATA / "skeleton_reference.txt"


@pytest.fixture(scope="session")
def full_skeleton(published_moves):
    """The published game split into its 118 critical segments."""
    from long_chess.skeleton import split_game

    return split_game(published_moves)


@pytest.fixture(scope="session")
def compressed_skeleton(request, full_skeleton):
    """The same game with every closed walk cancelled out.

    Cached across runs keyed by the PGN's hash *and* the hash of the
    skeleton package's sources, so a change to the compression code (or the
    serialisation it round-trips through) invalidates the cache rather than
    silently testing yesterday's output.
    """
    import long_chess.skeleton as skeleton_pkg
    from long_chess.skeleton import compress, from_dict, to_dict

    digest = hashlib.sha256(REFERENCE_PGN.read_bytes())
    for source in sorted(Path(skeleton_pkg.__file__).parent.glob("*.py")):
        digest.update(source.read_bytes())
    key = f"long_chess/compressed-skeleton-{digest.hexdigest()[:16]}"
    cached = request.config.cache.get(key, None)
    if cached is not None:
        return from_dict(cached)
    compressed = compress(full_skeleton)
    request.config.cache.set(key, to_dict(compressed))
    return compressed


@pytest.fixture(scope="session")
def published_moves(request):
    """The published game as a move list, cached across runs by content hash."""
    import chess

    if not REFERENCE_PGN.exists():
        pytest.skip("reference PGN missing; run scripts/fetch_reference.py")
    digest = hashlib.sha256(REFERENCE_PGN.read_bytes()).hexdigest()
    key = f"long_chess/reference-moves-{digest[:16]}"
    cached = request.config.cache.get(key, None)
    if cached is not None:
        return [chess.Move.from_uci(uci) for uci in cached]
    from long_chess.verifier import moves_from_pgn

    moves = moves_from_pgn(REFERENCE_PGN)
    request.config.cache.set(key, [move.uci() for move in moves])
    return moves




@pytest.fixture(scope="session")
def reference_skeleton():
    """Tom 7's hand-built skeleton, lifted out of longest.cc.

    Independent of our compression, so it is a real check rather than a
    restatement of what our own code produced.
    """
    from long_chess.skeleton import split_game
    from long_chess.verifier import moves_from_san

    if not REFERENCE_SKELETON.exists():
        pytest.skip("reference skeleton missing")
    return split_game(moves_from_san(REFERENCE_SKELETON.read_text(encoding="utf-8")))

