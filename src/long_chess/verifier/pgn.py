"""Reading games into move lists.

Kept minimal on purpose: parsing is not judging. Whatever comes out of here is
still only a candidate until :func:`~long_chess.verifier.game.verify_game`
accepts it.
"""

from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn


def moves_from_pgn(path: str | Path) -> list[chess.Move]:
    """Read the first game of a PGN file as a list of moves.

    ``chess.pgn`` is forgiving by design: a token it cannot parse is recorded on
    ``game.errors`` and the rest of the game is read anyway. Silence there would
    mean a truncated move list arriving at the verifier, which would then report
    a short game as legal rather than as a parse failure — so the errors are
    raised rather than collected.
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        game = chess.pgn.read_game(handle)
    if game is None:
        raise ValueError(f"no game found in {path}")
    if game.errors:
        first = "; ".join(str(error) for error in game.errors[:3])
        raise ValueError(
            f"{len(game.errors)} parse error(s) in {path}: {first}"
            f"{' ...' if len(game.errors) > 3 else ''}"
        )
    return list(game.mainline_moves())


def moves_from_uci(text: str) -> list[chess.Move]:
    """Read whitespace-separated UCI moves."""
    return [chess.Move.from_uci(token) for token in text.split()]


def moves_from_san(text: str, board: chess.Board | None = None) -> list[chess.Move]:
    """Read whitespace-separated SAN moves, ignoring move numbers.

    SAN is context-dependent, so this walks a board as it parses. An illegal
    move raises here rather than at verification time.
    """
    board = board.copy(stack=False) if board is not None else chess.Board()
    moves: list[chess.Move] = []
    for token in text.split():
        if token.endswith(".") or token in {"1-0", "0-1", "1/2-1/2", "*"}:
            continue
        move = board.parse_san(token)
        moves.append(move)
        board.push(move)
    return moves
