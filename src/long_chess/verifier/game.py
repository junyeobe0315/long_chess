"""The independent game verifier.

A move sequence is a result only if this class accepts it. Nothing here may
depend on how the moves were produced.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import chess

from .rules import (
    RepetitionKey,
    Termination,
    classify_position,
    is_critical,
    repetition_key,
)
from .trace import TraceRecord


class VerificationError(Exception):
    """The move sequence is not a legal game."""


class IllegalMove(VerificationError):
    def __init__(self, ply: int, move: chess.Move, fen: str) -> None:
        super().__init__(f"ply {ply}: illegal move {move.uci()} in {fen}")
        self.ply = ply
        self.move = move
        self.fen = fen


class GameAlreadyOver(VerificationError):
    def __init__(self, ply: int, termination: Termination) -> None:
        super().__init__(
            f"ply {ply}: game already ended by {termination.value}; "
            "no further move is playable"
        )
        self.ply = ply
        self.termination = termination


class GameVerifier:
    """Replays a game while enforcing the FIDE automatic termination rules.

    Usage::

        v = GameVerifier(trace=True)
        for move in moves:
            if v.push(move).is_over:
                break
    """

    def __init__(
        self,
        board: chess.Board | None = None,
        *,
        trace: bool = False,
    ) -> None:
        self.board = board.copy(stack=False) if board is not None else chess.Board()
        self.repetitions: dict[RepetitionKey, int] = {repetition_key(self.board): 1}
        self.plies = 0
        self.critical_plies: list[int] = []
        # Classify the starting position too. A board handed in already
        # checkmated, stalemated or down to dead material is not a game with
        # zero moves played — it is not a game at all, and silently accepting
        # it would let a caller "verify" moves that could never be made.
        self.termination = classify_position(
            self.board, self.repetitions[repetition_key(self.board)]
        )
        self.trace: list[TraceRecord] | None = [] if trace else None
        if self.trace is not None:
            self.trace.append(
                TraceRecord(
                    ply=0,
                    fen=self.board.fen(),
                    uci="",
                    critical=False,
                    halfmove_clock=self.board.halfmove_clock,
                    repetitions=1,
                    termination=Termination.CONTINUE.value,
                )
            )

    @property
    def critical_count(self) -> int:
        """Pawn moves and captures played so far.

        Note this does *not* include a final checkmate that is neither, even
        though the segment decomposition counts it as one. Use
        :attr:`GameResult.critical_count` for the game-level number.
        """
        return len(self.critical_plies)

    def push(self, move: chess.Move) -> Termination:
        """Play one move and return why the game ended, or CONTINUE."""
        if self.termination.is_over:
            raise GameAlreadyOver(self.plies, self.termination)
        if move not in self.board.legal_moves:
            raise IllegalMove(self.plies + 1, move, self.board.fen())

        critical = is_critical(self.board, move)
        self.board.push(move)
        self.plies += 1
        if critical:
            self.critical_plies.append(self.plies)

        key = repetition_key(self.board)
        count = self.repetitions.get(key, 0) + 1
        self.repetitions[key] = count

        self.termination = classify_position(self.board, count)

        if self.trace is not None:
            self.trace.append(
                TraceRecord(
                    ply=self.plies,
                    fen=self.board.fen(),
                    uci=move.uci(),
                    critical=critical,
                    halfmove_clock=self.board.halfmove_clock,
                    repetitions=count,
                    termination=self.termination.value,
                )
            )
        return self.termination

    def push_uci(self, uci: str) -> Termination:
        return self.push(chess.Move.from_uci(uci))


@dataclass(frozen=True, slots=True)
class GameResult:
    plies: int
    termination: Termination
    critical_plies: tuple[int, ...]
    final_fen: str
    trace: tuple[TraceRecord, ...] | None

    @property
    def critical_count(self) -> int:
        """Critical *segments*, which is what ``K`` means in ``L = 150K - S - Σδ``.

        Quiet moves after the last critical one form a closing segment of their
        own, and it counts. That is obvious for a checkmate — mate outranks the
        75-move draw, so the segment runs to its end and then some — but it is
        just as true when the game ends by the 75-move rule, by fivefold
        repetition, or in stalemate. Those endings are what the bound's draw case is
        made of, and counting the closing segment only for mate would understate
        K for every one of them.

        A game whose last move is itself critical has no closing segment, and a
        game still in progress has not closed one yet.
        """
        k = len(self.critical_plies)
        closing_is_quiet = (
            not self.critical_plies or self.critical_plies[-1] != self.plies
        )
        if self.termination.is_over and closing_is_quiet:
            k += 1
        return k


def verify_game(
    moves: Iterable[chess.Move],
    board: chess.Board | None = None,
    *,
    trace: bool = False,
    require_all_moves: bool = True,
) -> GameResult:
    """Replay ``moves`` and return the result.

    Raises :class:`VerificationError` if a move is illegal, if the starting
    position is already over, or — when ``require_all_moves`` is set — if the
    game ends before the moves run out.
    """
    # Materialised up front. Leftover moves after an early termination used to
    # be counted by re-reading the input, which a one-shot generator cannot do:
    # a game with moves after its checkmate passed silently, which is precisely
    # the thing this check exists to catch.
    moves = list(moves)

    verifier = GameVerifier(board, trace=trace)
    if verifier.termination.is_over:
        raise VerificationError(
            f"the starting position is already over by "
            f"{verifier.termination.value}: {verifier.board.fen()}"
        )

    consumed = 0
    for move in moves:
        consumed += 1
        if verifier.push(move).is_over:
            break

    leftover = len(moves) - consumed
    if require_all_moves and leftover:
        raise VerificationError(
            f"game ended at ply {verifier.plies} by "
            f"{verifier.termination.value} with {leftover} move(s) unplayed"
        )

    return GameResult(
        plies=verifier.plies,
        termination=verifier.termination,
        critical_plies=tuple(verifier.critical_plies),
        final_fen=verifier.board.fen(),
        trace=tuple(verifier.trace) if verifier.trace is not None else None,
    )
