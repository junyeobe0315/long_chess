"""Trying to break the home-rank lemma on a real board.

The optimality result rests on one claim: while the defender's pawns are all
still on their home rank, an attacking pawn stops four moves short of
promoting. Everything else in the model either follows from counting or is
checked elsewhere, so this is the thing to attack.

The search plays real chess. The defender is restricted to quiet moves, which
is what "the defender makes no critical move in this block" means, and the
attacker may do anything except take a defender pawn — that case is the
lemma's own escape hatch and is accounted for separately.

**A search that finds nothing proves nothing unless it can find something.**
So the same search runs in a mode where taking defender pawns is allowed, where
a pawn *can* get through. If that mode fails too, the search is broken and its
silence in the strict mode means only that it is not looking properly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import chess


@dataclass
class AttackResult:
    """How far the attacker got."""

    strategy: str
    allow_pawn_captures: bool
    plies: int
    best_pawn_moves: int
    """Most moves any single attacking pawn made."""

    furthest_rank: int
    """Closest an attacking pawn came to promoting, as a rank number."""

    reached_home_rank: bool
    invariant_breaks: int
    """Times the defender's home rank was not full of its pawns.

    Should stay zero in strict mode: the defender's pawns cannot move and
    cannot be taken, so nothing can disturb them.
    """

    moves_played: list[str] = field(default_factory=list)


def _quiet_moves(board: chess.Board) -> list[chess.Move]:
    """Legal moves that are neither a capture nor a pawn move."""
    out = []
    for move in board.legal_moves:
        if board.is_capture(move):
            continue
        piece = board.piece_at(move.from_square)
        if piece is not None and piece.piece_type == chess.PAWN:
            continue
        out.append(move)
    return out


def _attacker_moves(
    board: chess.Board,
    defender: chess.Color,
    *,
    allow_pawn_captures: bool,
) -> list[chess.Move]:
    """Everything the attacker may play.

    In strict mode, taking a defender pawn is forbidden: that is the one thing
    the lemma concedes opens the home rank, and it costs six of the ninety-six
    pawn moves, which K = 118 has no room for.
    """
    out = []
    for move in board.legal_moves:
        if not allow_pawn_captures and board.is_capture(move):
            victim = board.piece_at(move.to_square)
            if board.is_en_passant(move) or (
                victim is not None
                and victim.piece_type == chess.PAWN
                and victim.color == defender
            ):
                continue
        out.append(move)
    return out


def _home_rank(colour: chess.Color) -> int:
    """The rank a colour's pawns start on, 1-indexed."""
    return 2 if colour == chess.WHITE else 7


def _pawn_rank(square: int, attacker: chess.Color) -> int:
    return (
        chess.square_rank(square) + 1
        if attacker == chess.WHITE
        else (8 - chess.square_rank(square))
    )


def attack(
    attacker: chess.Color,
    *,
    plies: int = 400,
    rng: random.Random | None = None,
    strategy: str = "focus",
    allow_pawn_captures: bool = False,
    record_moves: bool = False,
) -> AttackResult:
    """Play out one attempt to walk a pawn onto the defender's home rank.

    Strategies:

    - ``focus`` — pick one pawn and push it whenever legal. The best way to
      maximise a single pawn's moves, which is what the lemma bounds.
    - ``spread`` — advance whichever pawn is furthest back.
    - ``random`` — no plan, as a control.
    """
    rng = rng or random.Random(0)
    defender = not attacker
    board = chess.Board()
    home = _home_rank(defender)

    # Track pawn identity by starting square so a pawn's moves can be counted
    # across file changes.
    identity = {square: square for square in chess.SQUARES if board.piece_at(square)}
    pawn_moves: dict[int, int] = {}
    target: int | None = None
    breaks = 0
    played: list[str] = []

    for ply in range(plies):
        # The defender's home rank should stay untouched in strict mode.
        if not allow_pawn_captures:
            occupied = sum(
                1
                for file in range(8)
                if (piece := board.piece_at(chess.square(file, home - 1))) is not None
                and piece.piece_type == chess.PAWN
                and piece.color == defender
            )
            if occupied != 8:
                breaks += 1

        if board.turn == defender:
            options = _quiet_moves(board)
            if not options:
                break
            move = rng.choice(options)
        else:
            options = _attacker_moves(
                board, defender, allow_pawn_captures=allow_pawn_captures
            )
            if not options:
                break
            move = _choose(board, options, identity, pawn_moves, target, strategy, rng)
            if strategy == "focus" and target is None:
                piece = board.piece_at(move.from_square)
                if piece is not None and piece.piece_type == chess.PAWN:
                    target = identity[move.from_square]

        piece = board.piece_at(move.from_square)
        is_pawn = piece is not None and piece.piece_type == chess.PAWN
        mover = identity.pop(move.from_square, move.from_square)
        identity.pop(move.to_square, None)
        identity[move.to_square] = mover
        if is_pawn and piece.color == attacker:
            pawn_moves[mover] = pawn_moves.get(mover, 0) + 1

        if record_moves:
            played.append(board.san(move))
        board.push(move)
        del ply

        if board.is_game_over():
            break

    ranks = [
        _pawn_rank(square, attacker) for square in board.pieces(chess.PAWN, attacker)
    ]
    furthest = max(ranks) if ranks else 0
    reached = any(
        chess.square_rank(square) + 1 == home
        for square in board.pieces(chess.PAWN, attacker)
    )

    return AttackResult(
        strategy=strategy,
        allow_pawn_captures=allow_pawn_captures,
        plies=board.ply(),
        best_pawn_moves=max(pawn_moves.values(), default=0),
        furthest_rank=furthest,
        reached_home_rank=reached,
        invariant_breaks=breaks,
        moves_played=played,
    )


def _choose(
    board: chess.Board,
    options: list[chess.Move],
    identity: dict[int, int],
    pawn_moves: dict[int, int],
    target: int | None,
    strategy: str,
    rng: random.Random,
) -> chess.Move:
    pawn_options = [
        move
        for move in options
        if (piece := board.piece_at(move.from_square)) is not None
        and piece.piece_type == chess.PAWN
    ]
    if not pawn_options:
        return rng.choice(options)

    if strategy == "focus" and target is not None:
        focused = [
            move for move in pawn_options if identity.get(move.from_square) == target
        ]
        if focused:
            return rng.choice(focused)
        return rng.choice(options)

    if strategy == "spread":
        return min(
            pawn_options,
            key=lambda move: pawn_moves.get(identity.get(move.from_square, -1), 0),
        )

    return rng.choice(pawn_options)


@dataclass
class Audit:
    """An exhaustive check at every position a rollout passes through.

    Stronger than the rollouts on their own. A rollout only shows that the one
    move it played did not break the lemma; this enumerates *every* legal
    attacker move at each position and checks none of them lands a pawn on the
    defender's home rank.
    """

    positions: int = 0
    moves_checked: int = 0
    violations: list[str] = field(default_factory=list)
    home_rank_intact: bool = True
    en_passant_offers: int = 0
    """Chances for the attacker to capture en passant.

    Should be zero: en passant needs a double push, which is a pawn move, which
    the defender is not making. Counted rather than assumed because it is the
    one rule that moves a pawn to a square it did not come from.
    """


def audit(
    attacker: chess.Color,
    *,
    attempts: int = 200,
    plies: int = 200,
    seed: int = 0,
) -> Audit:
    """Enumerate every attacker move at every position of many rollouts."""
    rng_seed = 0
    report = Audit()
    defender = not attacker
    home = _home_rank(defender)
    home_squares = {chess.square(file, home - 1) for file in range(8)}

    for index in range(attempts):
        rng = random.Random(f"{seed}:{index}")
        board = chess.Board()
        strategy = ("focus", "spread", "random")[index % 3]
        target: int | None = None
        identity = {sq: sq for sq in chess.SQUARES if board.piece_at(sq)}
        pawn_moves: dict[int, int] = {}

        for _ in range(plies):
            if any(
                (piece := board.piece_at(square)) is None
                or piece.piece_type != chess.PAWN
                or piece.color != defender
                for square in home_squares
            ):
                report.home_rank_intact = False

            if board.turn == attacker:
                report.positions += 1
                if board.has_legal_en_passant():
                    report.en_passant_offers += 1
                # Every legal move, not just the one about to be played.
                for move in board.legal_moves:
                    report.moves_checked += 1
                    piece = board.piece_at(move.from_square)
                    if piece is None or piece.piece_type != chess.PAWN:
                        continue
                    if move.to_square not in home_squares:
                        continue
                    victim = board.piece_at(move.to_square)
                    takes_defender_pawn = (
                        victim is not None
                        and victim.piece_type == chess.PAWN
                        and victim.color == defender
                    )
                    if not takes_defender_pawn:
                        report.violations.append(f"{board.fen()} allows {move.uci()}")

                options = _attacker_moves(board, defender, allow_pawn_captures=False)
                if not options:
                    break
                move = _choose(
                    board, options, identity, pawn_moves, target, strategy, rng
                )
                piece = board.piece_at(move.from_square)
                if strategy == "focus" and target is None and piece.piece_type == 1:
                    target = identity[move.from_square]
                if piece.piece_type == chess.PAWN and piece.color == attacker:
                    mover = identity.get(move.from_square, move.from_square)
                    pawn_moves[mover] = pawn_moves.get(mover, 0) + 1
            else:
                options = _quiet_moves(board)
                if not options:
                    break
                move = rng.choice(options)

            mover = identity.pop(move.from_square, move.from_square)
            identity.pop(move.to_square, None)
            identity[move.to_square] = mover
            board.push(move)
            if board.is_game_over():
                break

    del rng_seed
    return report


def hunt(
    attacker: chess.Color,
    *,
    attempts: int = 400,
    plies: int = 400,
    allow_pawn_captures: bool = False,
    seed: int = 0,
) -> AttackResult:
    """Run many attempts and keep the one that got furthest."""
    best: AttackResult | None = None
    for index in range(attempts):
        strategy = ("focus", "spread", "random")[index % 3]
        result = attack(
            attacker,
            plies=plies,
            rng=random.Random(f"{seed}:{index}"),
            strategy=strategy,
            allow_pawn_captures=allow_pawn_captures,
        )
        if best is None or (result.best_pawn_moves, result.reached_home_rank) > (
            best.best_pawn_moves,
            best.reached_home_rank,
        ):
            best = result
    assert best is not None
    return best
