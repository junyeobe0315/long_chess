"""The home-rank lemma as a proof, not a sample.

Seven million moves without a counterexample is evidence. This is the argument
those moves were evidence *for*, written as an induction whose every appeal to
the rules of chess is discharged by a finite check.

──────────────────────────────────────────────────────────────────────────────
THEOREM.  Fix colours A (attacker) and D (defender). Consider any position
reachable from the initial position by moves satisfying

    R1.  every D move is quiet — neither a capture nor a pawn move;
    R2.  no A move captures a D pawn.

Then every square of D's pawn home rank still holds the D pawn that started
there; no A pawn ever stands on that rank; and no A pawn makes more than four
moves.
──────────────────────────────────────────────────────────────────────────────

PROOF.

*Part 1 — the home rank never changes.* Induction on the number of moves.

  Base.  The initial position has D's eight pawns on their home rank.   [H0]

  Step.  Suppose it holds, and let m be a move permitted by R1 and R2. A move
  alters the occupancy of its own from- and to-squares, and of no others except
  the rook's two squares when castling and the captured pawn's square when
  capturing en passant.                                                  [H5]

  (a) m does not start on the home rank. By hypothesis that square holds a D
      pawn. Only the side to move may move it                            [H1],
      so it would have to be D moving its own pawn — a pawn move, excluded by
      R1.

  (b) m does not end on the home rank. By hypothesis that square is occupied,
      and a move onto an occupied square is a capture of an enemy piece  [H2].
      D capturing is excluded by R1; A capturing a D pawn is excluded by R2.

  (c) Castling touches only the back ranks, never a pawn home rank       [H3].

  (d) En passant removes a pawn from rank 4 or rank 5, never from a pawn home
      rank                                                               [H4].
      (It also needs a double push by the victim's side; were the victim D's,
      that would be a D pawn move, excluded by R1.)

  No case alters a home-rank square, so the property survives m.  ∎

*Part 2 — no A pawn reaches D's home rank.* Standing there requires a move
ending there, which (b) forbids.  ∎

*Part 3 — at most four moves.* A pawn move advances exactly one rank, or two
from its own home rank and only there                                    [H6].
An A pawn therefore never moves backwards, and by Part 2 it never occupies D's
home rank, nor the rank beyond it — reaching that would need a step from D's
home rank, or a double push from a rank that is not its own home rank. Its
range is the four ranks in between, and each move costs at least one of them.

Four is attained: four single pushes.  ∎
──────────────────────────────────────────────────────────────────────────────

Each ``[Hn]`` is a claim about the rules of chess rather than about this
argument. H0, H3 and H4 have finitely many cases and are settled by exhausting
them. H1, H2, H5 and H6 hold for every position there is, so no enumeration
could settle them — they are read off the FIDE laws, and the corpus check below
confirms that the move generator this project runs on agrees. That is a check
on the tooling, not on the mathematics.

Which is which is recorded in every obligation and printed in the report,
because the difference is the whole distinction between a proof and a lot of
evidence.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass

import chess

PAWN_HOME_RANKS = (1, 6)
"""Zero-indexed: rank 2 for White, rank 7 for Black."""

BACK_RANKS = (0, 7)


@dataclass(frozen=True, slots=True)
class Obligation:
    """One claim the proof leans on, and how it was settled."""

    tag: str
    claim: str
    method: str
    """``exhaustive`` where the cases are finite, otherwise the corpus size."""

    discharged: bool
    detail: str
    cases: int = 0
    """How many instances the check actually inspected.

    Recorded numerically because a check that saw nothing passes vacuously, and
    the tests assert this is non-trivial.
    """

    def describe(self) -> str:
        mark = "ok  " if self.discharged else "FAIL"
        return (
            f"  [{self.tag}] {mark} {self.claim}\n        {self.method}: {self.detail}"
        )


def corpus(games: int = 120, plies: int = 160, seed: int = 0) -> Iterator[chess.Board]:
    """Positions to check the non-finite claims against.

    Deliberately varied rather than restricted to the lemma's own rules: the
    claims [H1], [H2] and [H6] are about chess itself, so they should hold
    everywhere, and testing them only inside the restriction would be testing
    them where they are least likely to fail.
    """
    for index in range(games):
        rng = random.Random(f"{seed}:{index}")
        board = chess.Board()
        for _ in range(plies):
            yield board.copy(stack=False)
            moves = list(board.legal_moves)
            if not moves:
                break
            # Bias towards pawn moves and captures so promotions, en passant
            # and back-rank traffic all actually occur.
            interesting = [
                move
                for move in moves
                if board.is_capture(move)
                or board.piece_at(move.from_square).piece_type == chess.PAWN
            ]
            board.push(
                rng.choice(interesting if interesting and rng.random() < 0.7 else moves)
            )
            if board.is_game_over():
                break


def check_initial_home_ranks() -> Obligation:
    """[H0] The initial position has eight pawns on each home rank."""
    board = chess.Board()
    ok = True
    for colour, rank in ((chess.WHITE, 1), (chess.BLACK, 6)):
        for file in range(8):
            piece = board.piece_at(chess.square(file, rank))
            if piece is None or piece.piece_type != chess.PAWN or piece.color != colour:
                ok = False
    return Obligation(
        tag="H0",
        claim="the initial position has eight pawns on each home rank",
        method="exhaustive",
        discharged=ok,
        detail="16 squares inspected",
        cases=16,
    )


def check_move_origin_ownership(boards: list[chess.Board]) -> Obligation:
    """[H1] A legal move starts on a square holding a piece of the side to move."""
    checked = 0
    bad = []
    for board in boards:
        for move in board.legal_moves:
            checked += 1
            piece = board.piece_at(move.from_square)
            if piece is None or piece.color != board.turn:
                bad.append(f"{board.fen()} / {move.uci()}")
    return Obligation(
        tag="H1",
        claim="a legal move starts on a piece of the side to move",
        method=f"{len(boards)} positions",
        discharged=not bad,
        detail=f"{checked:,} moves, {len(bad)} exceptions",
        cases=checked,
    )


def check_occupied_target_is_capture(boards: list[chess.Board]) -> Obligation:
    """[H2] A move onto an occupied square captures an enemy piece there."""
    checked = 0
    bad = []
    for board in boards:
        for move in board.legal_moves:
            occupant = board.piece_at(move.to_square)
            if occupant is None:
                continue
            checked += 1
            if occupant.color == board.turn or not board.is_capture(move):
                bad.append(f"{board.fen()} / {move.uci()}")
    return Obligation(
        tag="H2",
        claim="a move onto an occupied square captures an enemy piece there",
        method=f"{len(boards)} positions",
        discharged=not bad,
        detail=f"{checked:,} such moves, {len(bad)} exceptions",
        cases=checked,
    )


def check_castling_stays_on_back_ranks() -> Obligation:
    """[H3] Castling moves only pieces on the back ranks.

    Exhaustive: there are four castling moves in chess, and every square any of
    them touches is generated and inspected here.
    """
    cases = []
    for fen, uci in (
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1"),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1"),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8g8"),
        ("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1", "e8c8"),
    ):
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci)
        assert board.is_castling(move)
        before = {square for square in chess.SQUARES if board.piece_at(square)}
        board.push(move)
        after = {square for square in chess.SQUARES if board.piece_at(square)}
        cases.append(before ^ after)

    touched = set().union(*cases)
    ok = all(chess.square_rank(square) in BACK_RANKS for square in touched)
    return Obligation(
        tag="H3",
        claim="castling touches only the back ranks",
        method="exhaustive",
        discharged=ok,
        detail=(
            f"all 4 castling moves; {len(touched)} squares change, "
            f"ranks {sorted({chess.square_rank(s) + 1 for s in touched})}"
        ),
        cases=4,
    )


def check_en_passant_victim_rank() -> Obligation:
    """[H4] En passant removes a pawn from rank 4 or 5, never a home rank.

    Exhaustive over the shape: both colours, every file the capture can happen
    on, every direction. The removed pawn's rank is a function of the capturing
    colour alone, so enumerating the files settles it.
    """
    victims = set()
    cases = 0
    for capturer in (chess.WHITE, chess.BLACK):
        for file in range(8):
            for direction in (-1, 1):
                victim_file = file + direction
                if not 0 <= victim_file <= 7:
                    continue
                if capturer == chess.WHITE:
                    fen = _en_passant_fen_white(file, victim_file)
                else:
                    fen = _en_passant_fen_black(file, victim_file)
                board = chess.Board(fen)
                for move in board.legal_moves:
                    if not board.is_en_passant(move):
                        continue
                    cases += 1
                    removed = move.to_square + (-8 if board.turn else 8)
                    victims.add(chess.square_rank(removed))

    ok = bool(victims) and all(rank not in PAWN_HOME_RANKS for rank in victims)
    return Obligation(
        tag="H4",
        claim="en passant removes a pawn from rank 4 or 5, never a home rank",
        method="exhaustive",
        discharged=ok,
        detail=(
            f"{cases} en-passant captures generated; victims on ranks "
            f"{sorted(rank + 1 for rank in victims)}"
        ),
        cases=cases,
    )


def _en_passant_fen_white(capturer_file: int, victim_file: int) -> str:
    board = chess.Board(None)
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(
        chess.square(capturer_file, 4), chess.Piece(chess.PAWN, chess.WHITE)
    )
    board.set_piece_at(
        chess.square(victim_file, 4), chess.Piece(chess.PAWN, chess.BLACK)
    )
    board.turn = chess.WHITE
    board.ep_square = chess.square(victim_file, 5)
    return board.fen()


def _en_passant_fen_black(capturer_file: int, victim_file: int) -> str:
    board = chess.Board(None)
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(
        chess.square(capturer_file, 3), chess.Piece(chess.PAWN, chess.BLACK)
    )
    board.set_piece_at(
        chess.square(victim_file, 3), chess.Piece(chess.PAWN, chess.WHITE)
    )
    board.turn = chess.BLACK
    board.ep_square = chess.square(victim_file, 2)
    return board.fen()


def check_move_changes_only_its_own_squares(boards: list[chess.Board]) -> Obligation:
    """[H5] A move changes only from, to, the castling rook, and the ep victim."""
    checked = 0
    bad = []
    for board in boards:
        for move in board.legal_moves:
            checked += 1
            before = {
                square: board.piece_at(square)
                for square in chess.SQUARES
                if board.piece_at(square)
            }
            probe = board.copy(stack=False)
            probe.push(move)
            after = {
                square: probe.piece_at(square)
                for square in chess.SQUARES
                if probe.piece_at(square)
            }
            changed = {
                square
                for square in chess.SQUARES
                if before.get(square) != after.get(square)
            }
            allowed = {move.from_square, move.to_square}
            if board.is_castling(move):
                back = chess.square_rank(move.from_square) * 8
                kingside = chess.square_file(move.to_square) > chess.square_file(
                    move.from_square
                )
                allowed |= {
                    back + (7 if kingside else 0),
                    back + (5 if kingside else 3),
                }
            if board.is_en_passant(move):
                allowed.add(move.to_square + (-8 if board.turn else 8))
            if changed - allowed:
                bad.append(f"{board.fen()} / {move.uci()}")
    return Obligation(
        tag="H5",
        claim="a move changes only its own squares, the castling rook and the "
        "en-passant victim",
        method=f"{len(boards)} positions",
        discharged=not bad,
        detail=f"{checked:,} moves, {len(bad)} exceptions",
        cases=checked,
    )


def check_pawn_rank_deltas(boards: list[chess.Board]) -> Obligation:
    """[H6] A pawn advances one rank, or two from its own home rank only."""
    checked = 0
    bad = []
    doubles_from = set()
    for board in boards:
        for move in board.legal_moves:
            piece = board.piece_at(move.from_square)
            if piece is None or piece.piece_type != chess.PAWN:
                continue
            checked += 1
            start = chess.square_rank(move.from_square)
            end = chess.square_rank(move.to_square)
            delta = (end - start) if piece.color == chess.WHITE else (start - end)
            if delta == 2:
                doubles_from.add(start)
                home = 1 if piece.color == chess.WHITE else 6
                if start != home:
                    bad.append(f"{board.fen()} / {move.uci()}")
            elif delta != 1:
                bad.append(f"{board.fen()} / {move.uci()}")
    return Obligation(
        tag="H6",
        claim="a pawn advances one rank, or two from its own home rank only",
        method=f"{len(boards)} positions",
        discharged=not bad,
        detail=(
            f"{checked:,} pawn moves, {len(bad)} exceptions; doubles seen only "
            f"from ranks {sorted(rank + 1 for rank in doubles_from)}"
        ),
        cases=checked,
    )


MAX_ATTACKER_PAWN_MOVES = 4
"""Part 3's conclusion. Four ranks of range, at least one spent per move."""


def verify(games: int = 120, plies: int = 160, seed: int = 0) -> list[Obligation]:
    """Discharge every obligation the proof appeals to."""
    boards = list(corpus(games=games, plies=plies, seed=seed))
    return [
        check_initial_home_ranks(),
        check_move_origin_ownership(boards),
        check_occupied_target_is_capture(boards),
        check_castling_stays_on_back_ranks(),
        check_en_passant_victim_rank(),
        check_move_changes_only_its_own_squares(boards[: len(boards) // 8 or 1]),
        check_pawn_rank_deltas(boards),
    ]
