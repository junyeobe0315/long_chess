# A second move generator, and what it is worth

> Backs the paper's Appendices A and B ([paper/main.tex](../paper/main.tex))
> **as future work**: the paper has not been updated and still lists
> python-chess's move generation as trusted. This document is the design and
> audit record for [`checker/longest_check.c`](../checker/longest_check.c), the
> C implementation that would let that sentence shrink.

## The sentence this is aimed at

Appendix B says what a sceptical reader has to trust. Two things are on the
list:

1. the summary of the FIDE termination rules — that Articles 5.2.2, 9.2.2,
   9.6.1 and 9.6.2 mean what this project takes them to mean;
2. for the mechanical checks only, the move generation of python-chess.

The second item covers a lot of ground. The witness verifier pushes 17,697 moves
through python-chess and asks it, at every ply, what is legal and whether the
game has ended. The corpus checks behind the home-rank lemma ([H1] [H2] [H5]
[H6]) enumerate legal moves with it. `scripts/certify.py` records the resulting
trace in the certificate. If python-chess generated a move it should not, or
failed to generate one it should, the failure would propagate silently through
all of it — and it would look exactly like success, because there is nothing
else in the repository to disagree with.

That is the specific hole. A library is the kind of thing a second
implementation can speak to.

## What replaying the witness alone proves — measured

Not as much as it looks like, and the numbers are worth writing down.

The 17,697-ply game contains:

| in the witness | count |
|---|---|
| castling moves played | **0** |
| en passant captures played | **0** |
| pawn double pushes played | **0** |
| positions where an en passant capture was legal at all | **0** |
| positions where a castling move was legal at all | 1,420 |
| promotions | 16 |

The middle row explains the two around it. A game built for length wastes no
tempo, and a pawn that advances two squares at once has spent a move it could
have spent twice; every one of the game's pawn moves is a single step. No double
push means no en passant offer, ever — not one position in 17,697 where the
capture was even available — and the kings, busy shuffling, never castle either.
So a program that implemented no castling rule and no en passant rule whatsoever
would replay this game correctly, ply for ply, all the way to mate.

This is not a hypothetical. Deleting the en passant clause from
`generate_pawn_moves` in `longest_check.c` — one `if` — and re-running the whole
orchestrator gives:

```
[FAIL] perft         28 checks, 23 passed, 5 failed  (max depth 3)
[FAIL] rule cases    30 cases, 29 passed, 1 failed
[PASS] witness       17697 plies, checkmate, 118 critical segments
[PASS] trace         17698 rows identical to data/longest.trace.tsv
[PASS] legal moves   17698 positions, 730845 moves, all identical
[PASS] corpus        2000 positions, 4 of 4 obligations discharged
```

A generator with en passant removed passes the replay, passes the per-ply trace
comparison, and passes the *complete legal-move dump at every position of the
game* — because the game never offers an en passant capture anywhere, so there
is no position at which the two implementations could disagree about one.

Only the two checks with an external standard catch it. That is the whole reason
they exist, and the reason the perft table comes first in every run.

The companion experiment points the other way. Over-restricting castling —
requiring the square the *rook* crosses to be unattacked, a common and wrong
reading of Art. 3.8b, which the file has a comment warning against — gives:

```
[FAIL] perft         28 checks, 19 passed, 9 failed
[FAIL] rule cases    30 cases, 26 passed, 4 failed
[PASS] witness       17697 plies, checkmate, 118 critical segments
[PASS] trace         17698 rows identical to data/longest.trace.tsv
[FAIL] legal moves   line 1756 differs
    python: 1755  ... e8d8 e8f7 e8f8 e8g8 f4f3 ...
    C     : 1755  ... e8d8 e8f7 e8f8 f4f3 ...
```

The replay still passes and the trace is still byte-identical, because the
witness never castles. The legal-move dump catches it at ply 1,755: Black could
have castled kingside there and did not, and one implementation knows it.

So the differentials are not vacuous, and neither are they sufficient. Each check
covers something the others do not. The third mutation in the table is not a
mutation at all: it is the state this file was actually in until the review that
added `--material-scan`, and the column is what every check said at the time.

| check | en passant removed | castling over-restricted | bishop clause missing |
|---|---|---|---|
| replay the witness | no | no | no |
| per-ply trace differential | no | no | no |
| legal-move dump differential | no | **yes** (ply 1,755) | no |
| corpus obligations | no | no | no |
| perft against published counts | **yes** | **yes** | no |
| hand-written rule cases | **yes** | **yes** | no |
| material scan | no | no | **yes** (10 of 5,103) |

Perft is blind to the last column because published node counts say nothing
about the ending rules, and every other check is blind to it because the
reference game never reaches a position where the material test can fire.

## Perft: what depth is enough

Perft counts leaf nodes of the legal-move tree to a fixed depth and compares
against numbers published outside this project — the Chess Programming Wiki's
"Perft Results" page, cross-checked by many independent engines over many years.
The suite runs seven positions: the starting array, Kiwipete, the rook-and-pawn
endgame that makes en passant interact with discovered check, a promotion
torture position, that position mirrored with colours swapped, and CPW positions
5 and 6.

Depth is not a free parameter, and the starting array shows why. With en passant
deleted entirely:

| depth | correct | en passant removed | difference |
|---|---|---|---|
| 4 | 197,281 | 197,281 | **0** |
| 5 | 4,865,609 | 4,865,351 | **−258** |

Depth 4 from the starting array catches nothing at all. The reason is a counting
argument, not luck: for White to capture en passant, a White pawn must first
reach the fifth rank, which takes two White pawn moves (plies 1 and 3), and a
Black pawn must then double-push alongside it (ply 4). The capture is ply 5.
Black capturing White needs a ply more still. So the tree below the starting
array contains exactly zero en passant captures down to depth 4 and exactly 258
of them at depth 5 — and a generator missing the rule is off by exactly that
number and no other.

This is why the suite is seven positions and not one. In Kiwipete a Black pawn
already stands on b4, so White's `a2-a4` on the first ply offers `bxa3` on the
second: the same defect shows there at depth 2, off by exactly one node. The
starting array is the position a reader would naturally check first and the one
that says least.

The default is depth 5 (42 checks, ~19 s). CI runs depth 6 (44 checks, ~25 s),
which is affordable there. The mirrored promotion position exists so that any
white/black asymmetry in the generator shows up as a difference between two
counts that must be equal, without needing an oracle at all.

**The oracle is external, and a typo in it is self-announcing.** If a published
number were transcribed wrongly, the check would fail loudly rather than pass
quietly, unless the typo happened to coincide with this program's own wrong
output. The rule is stated in the file and should stay stated: a number in that
table is never edited to match this program.

## Why C, and why one file

The point of a second implementation is that it fails differently from the
first. Everything about the choice follows from that:

- **A different language.** Not a second Python program: it would share the
  interpreter, the integer semantics, and the temptation to import `chess` "just
  for the FEN parsing".
- **A different board representation.** python-chess is bitboard-based, and its
  legality filtering is bitboard-shaped. `longest_check.c` is a 0x88 mailbox with
  pseudo-legal generation filtered by make / king-attacked / unmake. Two
  implementations that share a representation tend to share its characteristic
  bugs: bitboards invite mistakes in mask arithmetic and in the en passant
  discovered-check case, mailboxes invite file wrap-around off the edge of the
  array. The 0x88 layout turns the second of those into a single `& 0x88` test,
  and make/test/unmake turns the first into no special case at all — an en
  passant capture that exposes the mover's own king along the rank is rejected
  by the same code that rejects any other self-check, because both pawns really
  do leave the board before the king is tested.
- **One translation unit, standard library only, no dynamic allocation.** A
  reviewer can read the file top to bottom in one sitting and needs no build
  system, no package manager, and no lock file to reproduce it. `gcc -std=c99
  -O2 -Wall -Wextra -Werror -pedantic` is the whole toolchain, and it must be
  silent.
- **Fixed-size arrays, sized so they cannot overflow.** 256 moves per position
  (no position has more than 218), 65,536 plies, 131,072 repetition slots. There
  is no allocator to fail and no leak to look for.
- **The answer is not compiled in.** Neither 17,697 nor 118 appears in the
  source. The length and the ending arrive as `--expect-plies` and
  `--expect-termination` and are compared against what the replay found. The ply
  ceiling is 65,536 exactly so that it cannot be read as knowledge of the result.

The file is written against the Laws, not against python-chess, and it was
written without reading python-chess. Wherever a reading is subtle the comment
cites the governing article, and says both which sentence is being implemented
and — more usefully — what the wrong reading would look like.

## The independence criteria

Stated plainly, so a reviewer can check each one rather than take "independent"
on trust:

1. **Different language and toolchain.** C99 against Python 3.13. Satisfied.
2. **Different board representation.** 0x88 mailbox against bitboards.
   Satisfied.
3. **Different legality strategy.** make / attacked / unmake against
   bitboard-based pin and check masks. Satisfied.
4. **No shared code and no shared data structures.** The C file imports nothing
   from this repository and nothing from python-chess. Satisfied.
5. **Independent input parsing.** The C reads the PGN and resolves the SAN
   itself. `Nge4` names a destination and leaves the reader to work out which
   knight can legally get there, so resolving SAN *is* move generation; taking a
   move list from another program would put that program's generator back inside
   the trusted chain. Satisfied.
6. **An external oracle for at least one check.** The perft table. Satisfied —
   and this is the only criterion that speaks to *both* implementations being
   wrong at once.
7. **Independent author.** **Not satisfied, and not satisfiable here.**

The last one is the important one, and it is why this document exists rather
than a line in the paper. Both implementations were written by the same person
from the same reading of the FIDE Laws. If that reading is wrong, both programs
are wrong in the same direction and agree perfectly, and every check in
`scripts/check_movegen.py` passes.

> This work reduces trust item 2 — the move generator. It does **not** reduce
> trust item 1 — the summary of the Laws. Appendix B's first sentence stands
> exactly as it did.

Two concrete places where item 1 is doing real work and item 2 is not:

- **Checkmate outranks the 75-move draw.** The witness's final ply is
  simultaneously mate and the 150th quiet ply of its segment. Both
  implementations apply mate first (FIDE 9.6.2's precedence clause) because both
  were written by someone who had read that clause. A reader who disagrees about
  the clause gets no help from their agreement.
- **Position identity under Art. 9.2.2.** Both exclude the halfmove clock and
  the move number, and both count an en passant right only when a legal en
  passant capture actually exists. Same reading, twice.

## Inside the file

### The repetition table

Fivefold repetition (Art. 9.6.1) needs positions counted, and counting them
needs a decision about what makes two positions the same one. Article 9.2.2:
the same player to move, the same pieces on the same squares, and the same
possible moves — which brings in castling rights and the right to capture en
passant, and leaves out the clock and the move number entirely.

Comparing whole FENs is therefore wrong in the worst possible way. The halfmove
clock makes every position look new, so no position ever repeats, so the
fivefold rule silently never fires, and nothing visible goes wrong.

The key is 35 plain bytes:

```
bytes 0..31   the 64 squares, a1 first, four bits each (piece codes run 0..14)
byte 32       side to move
byte 33       castling rights
byte 34       the file of a legal en passant capture, or 8 for "none"
```

Byte 34 is the subtle one. A pawn that has just double-pushed does not create a
repetition-relevant difference unless an enemy pawn can actually take it — a
right that cannot be exercised is not a difference in the possible moves. The
file therefore records whether a **legal** en passant capture exists, not
whether the previous move was a double push. (`clean_castling_rights()` and
`has_legal_en_passant()` are the corresponding decisions on the Python side; the
two implementations reached the same reading separately, which is worth exactly
as much as criterion 7 above allows.)

The table is open addressing over a fixed array of 131,072 slots, and **each
slot stores the whole 35-byte key**. The hash — FNV-1a — only chooses where to
start probing; equality is decided by `memcmp` over all 35 bytes. A collision
therefore costs one extra probe and cannot produce a wrong count.

There is no Zobrist hashing here, deliberately, and it is the one place where
the file is slower than it could be. A Zobrist scheme asks the reader to trust
that 64 random 64-bit numbers never collide over a 17,697-ply run. That is
almost certainly true and it is exactly the kind of "almost certainly" this
program exists to avoid. A miscounted repetition is a wrong verdict about a
game, and there would be nothing left to see afterwards.

Sizing: at most 65,537 distinct positions can ever be entered, which is half the
slots, so the table can never fill. The insert function still reports failure
rather than wrapping, because a silent wrap would corrupt every count after it.

### The rule cases

Thirty-three hand-written positions, each naming the article it pins. They cover what
perft cannot: perft counts nodes and so is blind to *why* a count is right, and
it says nothing at all about checkmate, stalemate, insufficient material or the
ending rules, which have no published node counts.

Several cases are stated as a complete legal-move list rather than as "this move
is legal". `ep-rank-pin-moveset` is the sharpest: the position
`8/8/8/K2pP2r/8/8/8/7k w - d6 0 1` is given with its six legal moves listed in
full, so the *absence* of `e5d6` is something a reader sees rather than something
they trust. The contrast case moves the white king from a5 to a4 and the same
capture becomes legal — one square of difference, opposite verdicts, and the
pair pins the reading rather than the answer.

The eleven material cases (Art. 5.2.2) are the ones to read sceptically, and an
earlier draft of this document got them wrong in a way worth recording. It said
the two implementations agreed on 5.2.2 *because they implement the same
approximation*. They did not implement the same approximation, and they did not
agree.

The C file stopped at one bishop per side: it called `K+B+B` against a bare king
alive, and pinned that as a deliberate "gap" against FIDE, on the reasoning that
no test of the piece inventory could see it. That reasoning was wrong twice
over. The position is dead for exactly the reason `K+B` is dead — bishops never
leave their square colour, so no king can be mated on the other one — and
python-chess, which the verifier in `src/long_chess/verifier/` decides 5.2.2
through, was already deciding it that way. The two programs disagreed on ten
inventories, and nothing in this repository noticed: the reference game ends in
checkmate with a queen on the board, so the material test never fires anywhere
in it, and the trace differential, the legal-move differential, the corpus and
perft all passed regardless.

The clause now turns on the colours present rather than the count, and the
disagreement is gone. But the fix worth having was not the clause; it was
`--material-scan`. The predicate reads nothing but the inventory, so its whole
domain is finite — knights and bishops of each square colour per player, and
whether any pawn, rook or queen is on the board — and `check_movegen.py` now
walks all 5,103 points of it and puts every one to python-chess. Agreement is
measured on every run instead of asserted in prose.

What that measurement is worth is still limited, and in the way the old sentence
was reaching for: both programs decide 5.2.2 by material alone, and material
alone is not a decision procedure for a dead position — see
[dead-positions.md](dead-positions.md). Two implementations of one approximation
agreeing does not make the approximation right. It does mean the two verifiers
cannot silently return different verdicts on the same game, which is what the
old sentence claimed without having checked, and it is the reason the check
exists.

The safety argument for the witness is unchanged and needs none of this: a game
ending in checkmate contains no dead position, because the rest of the game
witnesses that mate is still reachable.

### The corpus walk

`--corpus N` walks random legal games and checks, at every position visited and
over every legal move of it, the four claims about the rules of chess that the
home-rank lemma leans on: [H1] a legal move starts on a piece of the side to
move; [H2] a move onto an occupied square captures an enemy piece there; [H5] a
move changes only the origin, the destination, the castling rook and the en
passant victim; [H6] a pawn advances one rank, or two from its own home rank
only.

These are corpus-checked on the Python side too, by
`src/long_chess/bound/invariant.py`, which is precisely why they are here:
passing there leaves python-chess inside the trusted base of Lemma 4.3.

A uniform random walk is a poor corpus — it shuffles pieces around the middle of
the board, and promotions, double pushes and en passant captures, which are
exactly what [H5] and [H6] would break on, almost never occur. So the walk is
biased towards pawn moves and captures. `invariant.py` biases its own walk the
same way and for the same reason; the two walks share the intent and nothing
else.

Because a biased walk is only as good as its bias, the run prints what it
actually saw:

```
corpus: among the moves checked, 446 castling moves, 120 en passant captures,
        2748 promotions
corpus: 20000 positions from 162 games, 4 of 4 obligations discharged
```

Nothing fails on those coverage numbers. They are there so the bias can be
judged instead of assumed — zero exceptions over a walk that never generated a
castling move would discharge [H5] without ever testing the clause that makes it
interesting.

## The orchestrator and CI

`scripts/check_movegen.py` locates a compiler (`$CC`, then `cc`, `gcc`, `clang`),
builds into a temporary directory, and runs everything: perft, the rule cases,
the material scan, the witness with `--trace` and `--dump-moves`, the two
differentials, the corpus,
and `data/rebuilt.pgn` when it is present. It prints one `[PASS]`/`[FAIL]` line
per check and returns nonzero on any failure.

A missing compiler is a **skip with exit 0**, not a failure — the same shape as
the CP-SAT tests skipping when OR-Tools is absent. Turning "no compiler
installed" into "the proof is broken" would be a lie, and a check that cries
wolf gets disabled.

The reference files come from the Python side on every run.
`data/longest.trace.tsv` is gitignored derived data, so a fresh checkout has no
stored trace to compare against; the script regenerates it with
`python -m long_chess.verifier` and says which of the two it used. Regenerating
is the stronger check anyway: it compares the C against what python-chess says
*now*, not against a file that happened to be lying around.

CI adds two things a laptop run does not:

- **A compiler matrix, gcc and clang.** Both legs compare byte for byte against
  the same Python-generated trace and the same legal-move dump, so agreement
  with the reference is agreement with each other. Two independently developed
  compilers producing the same 730,845 moves is a real check against a
  miscompilation, which is otherwise a failure mode that no amount of reading
  the source would find.
- **A sanitizer run.** `-fsanitize=address,undefined` over the witness, the rule
  cases, the corpus walk and a depth-4 perft. The file has no allocator, so this
  is not about
  leaks: it is about the fixed-size arrays. An index that ran one past the end of
  the move list or the game array would, in a `-O2` build, quietly read
  neighbouring static memory and produce a plausible wrong answer. Under
  AddressSanitizer it stops.

## Honest limits

- **Author independence is absent.** Criterion 7. Everything else in this
  document is subordinate to it. Two implementations of the same misreading agree
  perfectly.
- **The ending rules have no external oracle.** Perft's published counts cover
  move generation and nothing else. Fivefold repetition, the 75-move rule, the
  precedence of mate over the 75-move draw, and Art. 5.2.2 are pinned only by the
  hand-written rule cases and by agreement between two programs that share an
  author. This is the weakest part of the artefact and should be read as such.
- **Both programs approximate Art. 5.2.2 by material.** Neither decides dead
  positions. The witness needs no such decision procedure — see
  [dead-positions.md](dead-positions.md) — and `--material-scan` establishes only
  that the two implement the *same* approximation, over all 5,103 inventories,
  not that the approximation is right. It is still worth running: the two
  disagreed until recently, and every other check passed while they did.
- **The corpus walk is random.** Fixed seeds make a run reproducible; they do not
  make it exhaustive. Zero exceptions over 20,000 positions is evidence, not
  proof.
- **The differentials cover one game.** 17,698 positions is a lot of positions,
  but they are the positions of a single, extremely unusual game — no castling,
  no en passant, and long stretches of knight shuffling. Perft and the corpus are
  what reach the rest of chess.
- **The PGN dialect is narrow.** The reader accepts the movetext of the files in
  `data/` and refuses a `[FEN]` tag rather than skipping it. It is a reader for
  this repository's games, not a general PGN library.
- **`-Werror` is a build-time contract, not a proof of anything.** A clean build
  under two compilers says the file has no diagnosable defects of the kinds those
  compilers diagnose.

## Deferred: certificate integration

`data/certificate/` records every mechanical verdict with a SHA-256 per artefact,
and `scripts/check_certificate.py` re-runs the whole thing and compares
`manifest.json` byte for byte. Nothing from the C checker is in it, and nothing
was added during this work.

**Why it was deferred.** `certify.py` refuses to run from a dirty worktree, by
design: a certificate whose provenance says `worktree_clean: true` has to have
been produced from a clean one. The worktree was dirty throughout this work
(uncommitted manuscript changes under `paper/`), so the certificate could not be
regenerated. Changing the manifest schema without regenerating would leave
`check_certificate.py` comparing a new-schema fresh run against an old-schema
stored file, which fails immediately and takes the `certificate` CI job with it.
The right order is: land the checker, commit, then extend the manifest and
regenerate in one step.

**What should be added.** A `movegen` block in `manifest.json`, alongside `game`
and `decisions`. The manifest is the run-invariant half — no timestamps, no
provenance, compared byte for byte across machines — so the block may only carry
values that are identical everywhere:

```
"movegen": {
  "source_sha256":    "<sha256 of checker/longest_check.c>",
  "perft_max_depth":  <depth run, e.g. 6>,
  "perft_checks":     <checks run>,
  "perft_failed":     0,
  "rule_cases":       <cases run>,
  "rule_cases_failed": 0,
  "corpus_seed":      1,
  "corpus_positions": <positions walked>,
  "obligations":      ["H1", "H2", "H5", "H6"],
  "replay": {
    "plies":             17697,
    "termination":       "checkmate",
    "critical_segments": 118,
    "final_fen":         "3k4/3Q4/4K3/8/8/8/8/8 b - - 150 8849"
  },
  "trace_sha256":       "<sha256 of the C-produced trace>",
  "legal_moves_sha256": "<sha256 of the C-produced legal-move dump>"
}
```

The two hashes are the load-bearing ones. `trace_sha256` must equal the manifest's
existing `artefacts["longest.trace.tsv"]` hash — the certificate would then record
that two independent implementations produced the same 1.5 MB trace, which is a
stronger statement than either hash alone. `legal_moves_sha256` pins the
730,845-move dump, whose only other record today is a `cmp` that leaves no trace.

The first of those two equalities already holds, and was checked by hand while
this document was being written. The certificate packs its own copy of the game,
so the comparison is against that copy:

```bash
gcc -std=c99 -O2 -Wall -Wextra -Werror -pedantic -o /tmp/lc checker/longest_check.c
/tmp/lc data/certificate/longest.pgn --expect-plies 17697 \
    --expect-termination checkmate --trace /tmp/cert.trace.tsv
sha256sum /tmp/cert.trace.tsv
# 348359d4d8240ab2142fbee966b08afb88a1d9556480aee622ac842103b695a1
python -c "import json; m = json.load(open('data/certificate/manifest.json')); \
    print(m['artefacts']['longest.trace.tsv'])"
# 348359d4d8240ab2142fbee966b08afb88a1d9556480aee622ac842103b695a1
```

The C program, knowing nothing of python-chess or of this repository, produces
byte for byte the trace whose hash the committed certificate already records.
What is missing is only that the certificate does not *say* so.

The compiler identity does **not** belong in the manifest: it varies by machine

The compiler identity does **not** belong in the manifest: it varies by machine
and would break the byte-for-byte comparison. It belongs in `certificate.json`'s
`provenance` block, next to `python`, `ortools` and `chess`:

```
"cc": "gcc",
"cc_version": "13.3.0"
```

`certify.py` would gain one step — build the checker and run it, exactly as
`scripts/check_movegen.py` already does — and would need to treat a missing
compiler the way it treats a missing solver, since a certificate that silently
omits a block is worse than one that records the omission. That last point is the
open design question and the reason this is a paragraph rather than a patch:
either the block is mandatory and `certify.py` requires a C compiler, or it is
optional and the manifest needs a `movegen: null` that `check_certificate.py`
knows how to compare.
