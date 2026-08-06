# Why segments can be planned independently

> Construction detail behind the rebuilt witness (paper §6). Not part of
> the upper-bound proof; the packer relies on it, the paper does not.

Everything from skeleton extraction onward rests on one claim:

> No position occurs in two different critical segments.

It licenses counting repetitions per segment rather than across the whole game,
which is what lets cycle cancellation cut inside a segment safely and lets the packer
pack all 118 segments without any of them being able to interfere.

It is usually stated as "critical moves are irreversible — a pawn cannot go
back and a captured piece cannot return". That is the right intuition but it is
not yet an argument, because the position is more than one pawn or one piece.
Here is the argument, and the machine check that goes with it.

## The potential

For a position, define

    Φ = (pieces on the board, total pawn steps still available)

where a pawn's remaining steps is its distance to the promotion rank — 6 for a
pawn on its home rank, 1 for one on the seventh. Order pairs lexicographically.
Implemented as `long_chess.skeleton.potential`.

At the initial position Φ = **(32, 96)**. That 96 is the same 96 as in "at most
96 pawn moves" in the K ≤ 118 bound; it is the same quantity counted the same
way.

## The argument

**Quiet moves leave Φ alone.** A quiet move is by definition neither a capture
nor a pawn move, so the piece count is untouched and no pawn changes rank. Φ is
therefore *constant* throughout a segment's bridge.

**Every critical move strictly lowers Φ.** Exactly two cases:

- A **capture** removes a piece, so the first component drops. Lexicographic
  order makes the second component irrelevant. En passant is a capture and is
  covered.
- A **pawn move that is not a capture** keeps the piece count — promotion
  replaces the pawn rather than adding a piece — and reduces the second
  component: a single push spends one step, a double push two, and a promotion
  spends the pawn's last one.

So Φ is constant within a segment and strictly decreasing between them.
Positions in different segments have different Φ. Φ is a function of the piece
placement alone, so different Φ means different placement, and placement is the
first field of `repetition_key`. Two positions in different segments therefore
cannot be the same position. ∎

The closing checkmate of a maximal game is a quiet move and does not lower Φ.
It does not need to: it closes the last segment because the game ends there,
and there is no later segment for its positions to collide with.

## The check

Two independent tests, both run over the full 17,697-ply game.

`potential()` monotonicity — every quiet move leaves Φ unchanged and every
critical move strictly lowers it:

```
quiet moves leaving the potential unchanged : 17579
critical moves strictly lowering it         : 117
violations                                  : 0
potential: start (32, 96) -> end (3, 0)
```

`find_cross_segment_repeats()` — the conclusion itself, checked directly by
walking all 17,697 ply and recording which segment each position first appeared
in. It returns an empty list.

The second is implied by the first, so having both is deliberate: the direct
check would catch a mistake in the argument, and the argument explains why the
direct check is not a coincidence of this one game.

## Where it could still break

The argument is about *any* legal game, not just this one, so rebuilt
skeletons and hypothetical longer games are covered too. Two caveats
worth keeping in mind:

- It says nothing about positions repeating *within* a segment. Those are
  exactly what cycle cancellation removes and what the four-occurrence budget
  in `WalkBudget` governs.
- Φ ignores castling rights and en-passant rights, which are also part of
  `repetition_key`. That only makes the conclusion stronger: two positions
  differing in those but agreeing on placement would still be different keys.
