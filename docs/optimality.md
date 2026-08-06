# The argument that 17,697 is optimal

> **The canonical statement of this argument is now the paper** —
> [paper/main.tex](../paper/main.tex), §§2–5, with the verification
> methodology in §7. This file remains the repository-side long form,
> including the full correction records, and is kept consistent with the
> paper rather than superseding it.

No legal game beats 17,697 ply. This is the whole chain that leads there, with
what each link rests on, because a result of this shape is worth exactly as much
as its weakest step.

**Status: our own formalisation, machine-assisted, not reviewed by anyone
else.** Read it as a claim with its reasoning exposed, not as a settled fact.

The proof is a counting argument. `long_chess.bound` carries it and uses no
solver. CP-SAT and `long_chess.model.independent` re-decide the same question by
two other routes and agree — they are cross-checks, not the proof.

## The chain

**1. `L = 150K − S − Σδ`.**
A critical move — a pawn move or a capture — resets the 75-move counter. Each
segment holds at most 149 reversible ply plus its critical move; a change in
the colour making critical moves costs exactly one more, by parity. Verified
against the published game, where it closes exactly with `K = 118, S = 3,
Σδ = 0`. *(`tests/test_known_game.py`)*

**2. `K = (P − O) + (C + T)`.** *(`long_chess.bound.pawns`)* `K` counts critical
segments: one per critical move, plus a closing segment when quiet moves follow
the last of them. Writing it this way is deliberate — **neither half knows how
the game ended**, so one bound covers checkmate, the 75-move rule, fivefold
repetition, stalemate and dead positions alike.

| | | |
|---|---|---|
| `P` | pawn moves | ≤ 96 |
| `C` | captures | ≤ 30 |
| `O` | overlaps — moves that are both | ≥ `f`, step 3 |
| `T` | the closing segment | 0 or 1 |

**3. `P − O ≤ 88`, from the origin pair.** The two pawns that start on file `i`
are that file's **origin pair**. The file is **resolved** when one of *those two
pawns* itself makes a diagonal pawn move — the only way a pawn changes file, and
therefore a capture, and therefore an overlap. Otherwise the pair is unresolved
and both its pawns live and die on file `i`.

An unresolved pair makes at most **ten** combined moves:

- while both are on the file they cannot pass, so with White on rank `2 + a` and
  Black on `7 − b` we need `2 + a < 7 − b`, and their combined moves are at most
  their combined advance `a + b ≤ 4`;
- one of them may then be captured **by some other piece**, and the survivor
  gets a whole lifetime of six. `4 + 6 = 10`.

Both halves are re-derived by `check_origin_pair_cap`, which exhausts a state
space strictly more permissive than chess — turn order ignored, no third piece
in the way, either pawn removable at any moment for free.

**Is 10 the real number, or just an upper bound?** The search returns a path
attaining it, but a witness inside a relaxation only shows that 10 is tight *for
the relaxation* — a fact about the search. The stronger claim needs a legal
game, and there is one, 24 ply long:

```
1. Nf3 a6  2. Ng1 a5  3. Nf3 a4  4. Ng1 a3  5. Nxa3 Nc6  6. Nc4 Rb8
7. a3 Nf6  8. a4 Ng8  9. a5 Nf6  10. a6 Ng8  11. a7 Nf6  12. a8=Q Ng8
```

Black's a-pawn walks `a7-a6-a5-a4-a3` — four moves — and is taken there by the
b1 knight, which is the case the old cap of 4 left out. The knight steps aside
and White's a-pawn walks the whole file and promotes: six more. Ten, with
neither pawn ever moving diagonally, so the a-file is unresolved throughout.
The constant is exactly right rather than merely safe.

A resolved pair is capped only by the pawns themselves, at 12. The eight pairs
partition the sixteen pawns, so their caps add:

    P ≤ min(96, 10·(8 − f) + 12·f) = min(96, 80 + 2f)          O ≥ f

`O ≥ f` because resolving file `i` takes a diagonal capture by a pawn of *that*
pair, and a diagonal capture has one mover, whose origin file is one file.
Distinct resolved files therefore demand distinct overlap moves.

Maximising `min(96, 80 + 2f) − f` over `f ≤ 8`:

| f | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| `P ≤` | 80 | 82 | 84 | 86 | 88 | 90 | 92 | 94 | 96 |
| `P − O ≤` | 80 | 81 | 82 | 83 | 84 | 85 | 86 | 87 | **88** |

Taking the maximum over `f` is what makes this a bound over *all* games rather
than a statement about games with eight overlaps. Asserting `overlaps ≥ 8`
outright is only true *because* `K = 118` forces it, and so argues in a circle.

**4. `C + T ≤ 30`, by cases and not by ending.** Thirty pieces can ever be
captured — 32 on the board, less the two kings.

- `C = 30` leaves the two kings alone. That is a dead position, so the game ends
  on that very move and `T = 0`.
- `C ≤ 29` leaves `T ≤ 1`, since there is at most one segment after the last
  critical move.

Both give 30. The two ways of reaching it are the same arithmetic seen twice:

    30 captures, no closing segment:   96 + 30 − 8 + 0 = 118
    29 captures, closing segment:      96 + 29 − 8 + 1 = 118

A checkmate is the second: the mating side must keep something to mate with, so
one of the 30 survives, and the mate itself may be quiet.

**5. `K ≤ 118`, and equality pins every term.**

    K = (P − O) + (C + T) ≤ 88 + 30 = 118

`equality_witnesses()` enumerates every `(f, P, O, C+T)` the bounds permit with
`K = 118` and finds exactly one: `f = 8, P = 96, O = 8, C + T = 30`. Enumerated
rather than argued, because "each term is bounded and the sum is exact, so all
of them are extreme" is how the free `overlaps ≥ 8` axiom got in. `K = 117`
admits many assignments, which is what makes the pinning at 118 a real fact
about the arithmetic rather than about the enumeration.

`P = 96` means **all sixteen pawns make six single-square moves and promote.**
That is what the rest of the argument runs on.

**6. Actors are not chosen.** A pawn move is made by that pawn's colour; a
capture by the colour that does not own the victim. There is no third kind of
critical move. So `S` depends on nothing but the order events are played in.
*(`tests/test_search.py`)*

**7. The home-rank lemma.** *(`check_home_rank_lemma`, `bound.invariant`)*
Before the enemy has moved a pawn, all eight squares of its home rank hold one.
A pawn arriving there can neither push through nor step aside, and the enemy's
other pieces cannot stand there either — the squares are occupied by pawns that
do not move, and quiet moves cannot change that. So a pawn reaching the rank in
front stops: **four moves, not six.**

The only way through is to capture one of those pawns, which costs all six of
*its* moves — and step 5 has no six moves to spare.

**8. `S ≥ 3`.** *(`long_chess.bound.blocks`)* Critical events fall into maximal
single-colour blocks, and the block sequence fixes `S`. Counting the virtual
Black critical move before ply 1, an alternating sequence of `n` blocks has
`S = n − 1` opening with Black and `S = n` opening with White, so `S ≤ 2` leaves
exactly five shapes. Every one is refuted below.

One seam to state explicitly, because the two definitions do not quite coincide.
`S` is measured over all `K` endpoints, and the last of those may be the
**terminal quiet segment** rather than a critical move. The refutations below
are statements about critical moves. They line up in one step:

> Deleting the optional terminal endpoint cannot increase the number of actor
> switches. So if the whole game has `S ≤ 2`, its critical-move actor sequence
> has `S ≤ 2` too, and is therefore one of the same five shapes.

Deleting it either leaves the shape alone — when its block holds critical moves
as well — or removes the last block entirely, and an alternating sequence one
block shorter has exactly one switch fewer. `check_terminal_endpoint_free()`
exhausts both readings of every shape up to twelve blocks, and
`switch_lower_bound()` refuses to return a bound if it ever fails.

**9. `L ≤ 17,697`, by cases on `K`.** *(`ply_bound()`)* This is where the
statement has to be careful, because **`S ≥ 3` is not a global fact** — every
step of step 8 runs on `P = 96` and `C ≥ 29`, both of which come from `K = 118`.

> `1. Nf3 Nf6  2. Ng1 Ng8`, played four times over, is a legal 16-ply game. The
> initial position appears for the fifth time on the last ply, so it ends in
> fivefold repetition. No pawn moved and nothing was captured, so `K = 1`; its
> single endpoint is a Black move, matching the virtual Black opening, so
> **`S = 0`**.

So the theorem is two cases, and only one of them needs step 8:

| | | |
|---|---|---|
| `K ≤ 117` | `L ≤ 150 × 117 = 17,550` | `S ≥ 0` is enough |
| `K = 118` | `L ≤ 150 × 118 − 3 = 17,697` | needs `S ≥ 3` |

`17,550 < 17,697`, so the second case is binding and `L ≤ 17,697`. The first case
needs no switch argument because giving up a whole critical segment costs 150
ply, and no game has 150 switches to win back against that.

The published game attains 17,697.

## Killing the five shapes

Everything here follows from step 5: `P = 96` and `C + T = 30` with `T ≤ 1`,
hence `C ≥ 29`.

**Units, not pieces.** The counting below is over the 32 *units* that start on
the board, each followed through the whole game, not over piece types. A unit
that began as a pawn is still that unit after it promotes. This matters because
`P = 96` promotes every pawn, so a pawn-origin unit captured later is captured
as a queen — and "only seven of a side's capturable units did not start as
pawns" is a statement about origins, which is what makes `14 − 7 = 7` correct.

### `B` and `W` — one colour only

`P = 96` needs all sixteen pawns to move. A pawn move is a critical move of its
own colour, so the colour with no block would have to make 48 critical moves
somewhere it has no block. Immediate.

### `B W` and `W B` — two blocks

Write the shape `(X, Y)`, so every X critical event precedes every Y critical
event. `C ≥ 29`, and Y can take at most the 15 capturable X units, so **X makes
at least 14 captures.** Every one of them is an X critical event, hence in the
first block, hence before Y has made a single critical move — so each victim
made none of its own. (Y may have moved pieces in that time; quiet moves are
free. What it has not done is move a pawn or capture.) Only 7 of Y's capturable
units did not start as pawns, so at least `14 − 7 = 7` of the victims are
pawn-origin Y units that never made a pawn move, and at least `7 × 6 = 42` pawn
moves are gone:

    P ≤ 96 − 42 = 54

against the 96 that `K = 118` demands. This needs no lemma.

### `B W B` — three blocks

The one shape counting alone does not kill, and the only one the home-rank lemma
is needed for.

White's critical events are all in the middle block. `C ≥ 29` and Black can take
at most the 15 capturable White units, so **White makes at least 14 captures**,
all in that middle block. Only 7 of Black's capturable units did not start as
pawns, so **at least 7 of White's victims are pawn-origin Black units**, taken
in the middle block. (By then they have promoted — `P = 96` sees to that — so
they are captured as pieces. The count is over origins.)

`P = 96` gives each of those units six *pawn* moves, and a unit makes its moves
before it is taken, so **all six fall in the first block.** Two things are then
true of the first block:

- **White makes no critical move in it.** It is a Black block. So every White
  move in it is quiet.
- **No White pawn is captured in it either.** A White pawn's six moves can only
  fall in the middle block, so a White pawn taken in the first block makes none
  of them — and `P = 96` has no six moves to give up.

Those are exactly the hypotheses of the home-rank lemma, which caps a Black pawn
at **four** moves while White's home rank is intact. Seven pawns needing six
apiece and allowed four:

    P ≤ 96 − 7 × 2 = 82

Contradiction. So `S ≥ 3`.

## The cross-checks

The counting above is the proof. Two other methods decide the same question, and
they exist because a counting argument written by the same person who wanted the
answer is not evidence on its own.

**CP-SAT.** *(`long_chess.model.abstract`)* Enumerate every shape — the block
sequences of the `K` segment endpoints, the same sequence `S` is measured
over — and ask whether `K = 118` fits. Deliberately a relaxation — it knows
nothing about squares, reachability, whether a capture is physically
available, or whether the quiet bridges between events exist — so every legal
game maps to a solution and infeasible means no legal game.

**Arithmetic.** *(`long_chess.model.independent`)* The same question with no
solver, declaring its own constants rather than importing them. It is an
**independent arithmetic cross-check**, not a second proof: it reads the same
`Shape` and works in the same numbers, and `tests/test_independent.py` pins its
literals against the canonical derivations so the two cannot drift silently.

```
                  checkmate                    draw
shape       S   K=118?   max K   no lemma   K=118?   max K   no lemma
B           0   INFEAS      64     INFEAS   INFEAS      64     INFEAS
W           1   INFEAS      64     INFEAS   INFEAS      64     INFEAS
B W         1   INFEAS     109     INFEAS   INFEAS     109     INFEAS
W B         2   INFEAS     109     INFEAS   INFEAS     109     INFEAS
B W B       2   INFEAS     115    OPTIMAL   INFEAS     115    OPTIMAL
W B W       3   INFEAS     115    OPTIMAL   INFEAS     115    OPTIMAL
B W B W     3  OPTIMAL     118    OPTIMAL  OPTIMAL     118    OPTIMAL
W B W B     4  OPTIMAL     118    OPTIMAL  OPTIMAL     118    OPTIMAL
```

All 16 shape×ending pairs agree, and every shape the counting proof refutes comes
back infeasible. Minimum feasible `S = 3` under both endings.

Which method says what: the `K=118?` and `no lemma` verdicts are CP-SAT's, and
`max K` is the arithmetic checker's maximum over its relaxation — an upper
bound on each shape's true ceiling, quoted so the margins are visible, not
claimed tight. (The single-block maxima read 71 until the checker was taught
that a colour with no enemy block cannot lose a unit — a necessary condition
the CP model had always imposed structurally. No verdict moved; 71 and 64 are
both a long way from 118.)

Two things to read off it. `B W B` and `W B W` become feasible with the lemma
switched off, which is the check that the lemma is doing the work its section
claims — and that the other refutations are not secretly leaning on it.

And the two ending columns are now **identical at every shape**. That is not the
ending being ignored: a draw really may take all 30 units and a checkmate at most
29. It is the trade coming out even everywhere, not just at 118 — the extra
capture is paid for exactly by the closing segment it gives up, which is what
`C + T ≤ 30` says. The columns used to differ, and only because the checkmate
branch was carrying a constraint that holds at 118 and nowhere else; see the
correction below.

## Why the model's UNSAT is worth anything

Only because it is a relaxation, and only because it accepts games that exist.

A constraint *stronger* than legality produces UNSAT indistinguishable from a
proof, which is the one failure that cannot be caught afterwards. Three
constraints came close to being exactly that mistake. Two were caught by review;
the third is the subject of the next section.

- The first version of the overlap bound modelled crossing as a pair of
  permutations with no file fixed by both. That is not a necessary condition —
  a pawn can leave its file and come back — and constraining too tightly makes
  the minimum too large, the `K` bound too small, and rules out legal games. It
  got 8 by luck. Replaced with the file lemma.
- The home-rank limit was first applied unconditionally, which forbids a pawn
  from capturing its way through. Legal, if ruinous. Now conditional on whether
  an enemy pawn has been taken.
- `ending` fell through to the draw branch for any unrecognised string. The draw
  branch has the higher capture ceiling, so a typo relaxed the model silently.
  It now raises.

And the check that catches the worst of it: **the model accepts the published
17,697-ply game**, with `P=96, C=29, O=8, T=1` and shape `B W B W`. If it did
not, every infeasible result above would be describing the model's own
constraints rather than chess. *(`tests/test_model.py::TestSoundness`)*

**That check is necessary and nowhere near sufficient, and it is worth being
blunt about why.** The false cap of 4 accepted the published game perfectly
happily — that game resolves all eight files, so `32 + 8f` and `80 + 2f` agree
on it exactly. A regression test built from one game can only catch constraints
that game violates. Soundness has to come from arguing each constraint
separately, which is what the table in
[abstract-model.md](abstract-model.md#constraints-and-which-direction-each-is-safe-in)
is for, and the two constraints that were wrong were both found by argument
rather than by that test.

## A correction: the checkmate branch was not a model of checkmate

The model's checkmate branch used to force **the mated side to lose all fifteen
of its capturable units**. That is not a property of checkmate. Scholar's mate —

```
1. e4 e5  2. Bc4 Nc6  3. Qh5 Nf6  4. Qxf7#
```

— is a legal checkmate in which Black has lost exactly one unit. Pinning that
game's profile (`P=2, C=1, O=0, T=0`, shape `W B W`, `K=3`) into the model
returned INFEASIBLE, so the documented claim "every legal game maps to a
solution" was **false** for every `K` other than 118.

At `K = 118` the constraint is derivable rather than assumed: `C + T = 30` with
`C ≤ 29` and `T ≤ 1` forces `C = 29, T = 1`, and 29 captures leave the two kings
and one non-king unit — which the mating side must own, since a lone king cannot
mate. So the mated side really is reduced to a lone king *there*. The verdicts
at 118 were therefore never affected, and neither was the counting proof, which
does not use the model at all.

What was affected is everything else the model was asked. The `max K` figures
reported for checkmate at lower targets were conditional on a constraint that
does not hold, and were not the general maxima they were presented as. The
branch now asserts only what checkmate implies — the mating side keeps at least
one non-king unit — and the checkmate maxima have risen to match the draw
column, which is what a genuinely general relaxation gives.

Two smaller gaps went with it. `overlaps` was bounded below by `f` but not above
by anything, so the solver could answer a low target with more overlaps than
pawn moves; `O ≤ P` and `O ≤ C` are both implied by legality and are now
imposed. And the arithmetic cross-check forced a *quiet* mate (`T = 1`), when a
mate delivered by a capture or a pawn move has `T = 0`.

## A correction: the unresolved cap was 4, and 4 is false

This is the serious one, because it was wrong in the direction that manufactures
proofs.

An earlier version of `bound.pawns` had

    UNRESOLVED_FILE_CAP = 4

with the reasoning: two pawns facing each other on a file cannot pass, White ends
on rank `2 + a` and Black on `7 − b` with `2 + a < 7 − b`, so `a + b ≤ 4`. That
argument is correct **only while both pawns are still on the file.** It says
nothing about what happens after one of them is captured, and a pawn captured by
some third piece leaves the other free to run.

### The counterexample

Legal, eight moves long, and checked with python-chess as a regression
*(`tests/test_bound.py::TestTheOldCapWasFalse`)*:

```
1. e4 a5  2. e5 a4  3. Bb5 Nc6  4. Bxa4 Rb8  5. Bb3 Nh6
6. a3 Ng4  7. a4 Nh6  8. a5
```

The a-file's origin pair:

| pawn | route | moves | diagonal moves |
|---|---|---|---|
| Black a-pawn | `a7-a5-a4`, then taken by the bishop | 2 | 0 |
| White a-pawn | `a2-a3-a4-a5` | 3 | 0 |

Neither ever moved diagonally, so the a-file is **unresolved** by definition —
and the pair has already made **five** moves against a cap that said four. The
game does not even have to be contrived; the bishop takes on a4 in the ordinary
course of play.

### Why it mattered

`UNRESOLVED_FILE_CAP = 4` fed straight into

    pawn moves ≤ 32 + 8f

which appeared in `bound.pawns`, in the CP-SAT model, and in the arithmetic
cross-check. It is a constraint **stronger than legality**: it rules out games
that exist. Every INFEASIBLE the model returned was therefore suspect, and an
UNSAT produced by an over-tight constraint looks exactly like a proof.

### Why the conclusion survives

The corrected cap is 10, and the corrected coupling is

    pawn moves ≤ 80 + 2f          (was 32 + 8f)

which is **weaker at every `f`** — it permits more games, as it must. The
maximum of `min(96, 80 + 2f) − f` is still 88, still at `f = 8`, still forcing
`P = 96` and `O = 8`. So `K ≤ 118` is unchanged, the equality conditions are
unchanged, and the `K = 118 ⟹ S ≥ 3` step is unchanged.

What did change is every margin, and they are all smaller:

| shape | max K, old (false) coupling | max K, corrected |
|---|---:|---:|
| `B W`, `W B` (draw) | 106 | 109 |
| `B W B` (both endings) | 112 | 115 |

`B W B` used to miss 118 by six and now misses by three. The old numbers were
not conservative — they were wrong, and wrong in the direction that flatters the
result. They are not preserved anywhere.

The checkmate column moved again, and further, when the checkmate branch itself
was corrected — see the next section. Both corrections push the same way: the
margins the project first reported were flattering artefacts of constraints that
did not hold.

The `S ≥ 3` argument was rewritten at the same time and no longer goes through
the model at all: `bound.blocks` refutes all five `S ≤ 2` shapes by counting,
and the sections above are that argument. The old `bound.blocks` left `B W B`
open to counting and deferred it to CP-SAT; it is now closed by hand, using the
home-rank lemma directly rather than as a solver constraint.

## Attacking the home-rank lemma

It is the load-bearing step — the only thing standing between `B W B` and a
17,698-ply game — so it was attacked directly rather than believed.
*(`long_chess.bound.adversary`, `scripts/attack_lemma.py`)*

The search plays real chess. The defender is restricted to quiet moves, which
is what "makes no critical move in this block" means, and the attacker may do
anything except take a defender pawn — the lemma's own escape hatch, accounted
for separately.

**The control comes first, because a search that finds nothing proves nothing
unless it can find something.** The same search runs with the restriction
lifted, where a pawn demonstrably can get through. `uv run python
scripts/attack_lemma.py`, at its defaults — 400 attempts, 300 ply, seed 7 —
which is seeded and reproduces exactly:

```
control: the restriction lifted, where a pawn CAN get through
  Black best single-pawn moves 6, reached home rank True   search works
  White best single-pawn moves 6, reached home rank True   search works

under the lemma's conditions
  Black best single-pawn moves 4 (lemma says at most 4), reached home rank False, home rank disturbed 0 times
  White best single-pawn moves 4 (lemma says at most 4), reached home rank False, home rank disturbed 0 times

exhaustive: every legal attacker move at every position visited
  Black 44,622 positions, 2,176,929 moves, 0 violations, 0 en-passant offers
  White 46,157 positions, 2,253,340 moves, 0 violations, 0 en-passant offers
```

Three things worth drawing out.

**Four is reached, not merely not-exceeded.** If the true limit were three the
model would still be sound but the constant would be wrong, so the tests assert
equality.

**The exhaustive pass checks every legal attacker move at each position, not
just the one played** — about 4.4 million moves across about 90,000 positions,
none of which lands a pawn on the defender's home rank without taking a pawn.
(An earlier version of this document quoted seven million across 140,000, which
no invocation of the script reproduces. The numbers above are the defaults, and
they are seeded.)

**En passant never becomes available.** It is the one rule that can put a pawn
on a square it did not walk to, and it needs a double push, which is a pawn
move, which the defender is not making. Counted rather than assumed: zero.

### And then the proof

Seven million moves is evidence. `long_chess.bound.invariant` is the argument
they were evidence *for*: an induction on moves, stated in full in that
module's docstring.

The shape of it. Suppose the defender's home rank holds its eight pawns, and
consider any move the restrictions permit. It cannot **start** there, because
that square holds a defender pawn and only the defender may move it, which
would be a pawn move. It cannot **end** there, because the square is occupied,
a move onto an occupied square is a capture, and neither side is allowed to
make that one. Castling touches only the back ranks. En passant removes a pawn
from rank 4 or 5. No case disturbs the rank, so it survives every move — and a
pawn that can never stand on it, and never moves backwards, has four ranks of
range and spends at least one per move.

Every appeal to the rules is tagged `[H0]`–`[H6]` and discharged separately:

| | claim | settled by |
|---|---|---|
| H0 | the initial position has eight pawns on each home rank | **exhaustive**, 16 squares |
| H1 | a legal move starts on a piece of the side to move | corpus |
| H2 | a move onto an occupied square captures an enemy piece | corpus |
| H3 | castling touches only the back ranks | **exhaustive**, all 4 castling moves |
| H4 | en passant removes a pawn from rank 4 or 5 | **exhaustive**, all 28 cases |
| H5 | a move changes only its own squares, the rook, the ep victim | corpus |
| H6 | a pawn advances one rank, or two from home only | corpus |

The distinction in that last column is the point. H0, H3 and H4 have finitely
many cases and are settled outright. H1, H2, H5 and H6 hold for every position
there is, so no enumeration could settle them — they are read off the FIDE
laws, and the corpus check confirms that the move generator this project runs
on agrees. **That is a check on the tooling, not on the mathematics.**

So the lemma is no longer resting on sampling. What remains resting on the
corpus is only whether python-chess implements four rules correctly.

## An earlier correction: the overlap term is coupled, not free

Kept because the shape of the mistake repeats. An earlier version of this
document claimed the result did not need the overlap bound at all, on the
strength of a table showing the verdicts unchanged with the floor dropped to
zero. **That table was wrong.** `solve()` was not passing the floor through to
`build()`, so both columns were the same run.

Finding it was the cross-check's doing. `long_chess.model.independent` and the
solver agreed at the default floor and disagreed once the floor moved, which is
exactly the disagreement a second implementation is for.

The underlying mistake was worse than the plumbing. `overlaps ≥ 8` was asserted
as a free axiom, and it is not one — it is only true *because* `K = 118` forces
every file to be resolved. Both the model and the cross-check now optimise over
`f` instead of assuming it, which is step 3 above.

## Where it could still be wrong

- **The model is a relaxation, so it cannot be too strong — unless one of the
  constraints above is.** That is exactly what happened with the unresolved cap,
  and it went unnoticed through a review. The constraint to attack now is the
  home-rank lemma, and the section above is what attacking it produced.
- **The counting proof is a hand argument.** It is checked by two independent
  methods and by the published game, but it is not machine-checked in the sense
  a proof assistant would mean, and neither is `S ≥ 3` for shapes past five
  blocks (they have `S ≥ 3` by inspection, which is the only place this argument
  is content to say "by inspection").
- **Dead positions.** `is_insufficient_material` is not a decision procedure for
  FIDE Article 5.2.2 (see [dead-positions.md](dead-positions.md)), so this
  verifier ends games *later* than FIDE. The bound uses exactly one
  dead-position fact — king against king — where the material test and FIDE
  agree, and it is used in the direction of a true statement about legal games.
  Everything else is left out, which loosens the model.
- **The block abstraction assumes the events partition into maximal
  single-colour runs**, which is the definition of S, and that a shape's
  feasibility does not depend on where within a block an event sits. The model
  drops all intra-block ordering, which is a relaxation, so this is safe.
- **No machine-checkable proof object.** CP-SAT emits none for UNSAT, so a
  third party has to re-run the model. `scripts/certify.py` exports all 32 —
  eight shapes under each ending, with and without the home-rank lemma — with
  a hash apiece.

## What is not claimed

That the concretiser is unnecessary. If the model had said `B, W, B` was
feasible, a candidate would still have had to be built on a real board. It said
infeasible, so there is nothing to build — but that also means the concretiser
has never been exercised, and with it the CEGAR loop that would have tightened
the model. Those remain unwritten.
