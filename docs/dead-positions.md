# `is_insufficient_material()` is not a dead-position test

> Backs §6 and §7.3 of the paper ([paper/main.tex](../paper/main.tex)):
> why the witness needs no dead-position decision procedure, and the one
> dead-position fact the upper bound uses.

FIDE Article 5.2.2 ends the game immediately when a position is *dead* — when
no series of legal moves can lead to checkmate for either side. python-chess's
`is_insufficient_material()` decides something narrower: whether the **material
on the board** could ever mate, ignoring how it is arranged.

The verifier uses it as a cheap first-pass check. It is not, and must not be
presented as, a decision procedure for Article 5.2.2.

## What it does and does not catch

Measured against python-chess 1.11.2:

| position | `is_insufficient_material()` | actually dead |
|---|---|---|
| K vs K | `True` | yes |
| K+B vs K | `True` | yes |
| K+N vs K | `True` | yes |
| K+N+N vs K | `False` | no (mate is possible, if not forcible) |
| K+B vs K+B, bishops on the same colour | `True` | yes |
| K+B vs K+B, opposite colours | `False` | no |
| K+R vs K | `False` | no |
| locked pawns, e.g. `7k/8/8/p1p1p1p1/P1P1P1P1/8/8/K7 w - - 0 1` | **`False`** | **yes** |

The last row is the gap. In that position every pawn is blocked by the pawn
directly in front of it and has no diagonal contact with any other, so no pawn
can ever move again. Only the kings can move and neither can ever be mated —
the position is dead by Article 5.2.2 — but the material-only test sees eight
pawns and says nothing.

The error is one-sided, which is the useful part:

> `is_insufficient_material() == True` implies dead.
> Dead does **not** imply `is_insufficient_material() == True`.

## Which direction is safe — and it is the opposite of what this said

An earlier version of this document had the two halves the wrong way round. The
error is worth keeping visible, because it is the same reasoning the whole
project turns on and it is easy to get backwards.

Our verifier ends games **later** than FIDE, since it misses dead positions and
plays on. So:

**The construction is the exposed side.** We claim a legal 17,697-ply game. If
a dead position occurred at, say, ply 9,000, FIDE says the game ended there and
our count is inflated — the claimed game would not be 17,697 ply of legal play.
Missing detections make our claimed length **too large**, which is exactly the
wrong direction for a lower bound.

**The upper bound is the safe side.** The model ignores dead positions entirely, so
the model permits games FIDE would have cut short. It bounds a superset of the
legal games, and bounding a superset bounds the subset. Leaving the constraint
out cannot cause a false UNSAT — omitting constraints only ever loosens a
model, and a looser model refutes less, not more.

## Why the construction is safe anyway

Not by the argument above, which was wrong, but by a much shorter one.

FIDE 5.2.2 makes a position dead when **no series of legal moves can lead to
checkmate**. Take any position at ply `i` of our game. The remaining moves of
the game are a series of legal moves, and they end in checkmate. So mate is
reachable from that position, and it is not dead.

> **A game that ends in checkmate contains no dead position.** Every position
> in it has the rest of the game as a witness.

Our game ends in checkmate — verified end to end — so the gap is not exercised
anywhere in it, and no further checking is needed. The same argument covers all
300 batch-generated games and anything else the packer produces, since the packer only
ever builds games ending in mate.

It does *not* cover hypothetical games ending in a draw, which is where a dead
position could genuinely sit unnoticed. Those are the model's business, and the model is the
safe direction.

## What the model does about it

Almost nothing, deliberately, and the one exception is worth stating precisely.

The model ignores every dead position **except king against king**. Every legal game —
including every one FIDE would have stopped at some other dead position — maps
to a solution of the model, so INFEASIBLE still means "no legal game", which is
all the bound needs.

### The one exception, and why it does not cut the wrong way

`C + T ≤ 30` is proved by cases (see
[optimality.md](optimality.md#the-chain)), and one of the cases is:

> 30 captures leaves the two kings alone on the board. That is dead, so the game
> ends on that move and there is no closing segment: `T = 0`.

That *is* a dead-position rule being used to shorten a game, which is the
tightening direction — the one that can invent an UNSAT. It is safe because it
is simply true. K vs K is the top row of the table above: `is_insufficient_material()`
and Article 5.2.2 agree on it, and no legal game continues past it. A constraint
that every legal game already satisfies excludes none of them.

Nothing else is claimed. In particular the locked-pawn row of the table — the
gap — is never appealed to in either direction. The model does not detect those
positions and does not need to: not detecting them lets it admit games FIDE
would have stopped, and admitting too much is the safe side of an upper bound.

The earlier version of this section said the model does *nothing* about dead positions.
That was one exception out of date, and the exception is the one that matters,
because it points the other way from the rest.
