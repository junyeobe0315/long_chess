# Claims map

Every machine-checked claim of the paper ([paper/main.pdf](paper/main.pdf)),
mapped to the code that decides it and the test that pins it. Statement
numbers refer to the current draft; the `\label` names in
[paper/main.tex](paper/main.tex) are the stable identifiers.

The paper's proof is a hand argument and is checkable without running
anything here. What this repository adds: the finite case analyses exhausted
mechanically, the witness verified ply by ply, the central case analysis
re-decided by two independent methods, and a byte-for-byte reproducible
certificate of all of it.

## Two tiers

| Tier | Needs | Command | Time (measured on one laptop) |
|---|---|---|---|
| **quick** | Python 3.13 + `uv sync --frozen` (no solver) | `make verify-quick` | ~8 s (test suite ~5 s) |
| **full** | `uv sync --frozen --extra solver` (adds CP-SAT), and a C compiler for the second move generator — without one that step skips rather than fails | `make verify-full` | ~45 s |

The test suite is a single ~5 s run: the witness verified end to end, every
constant and refutation of the counting proof, the solver-free cross-check,
and the regression pins. The heavy end-to-end work is not in pytest but in
the scripts the full tier runs — `check_certificate.py` repacks and
re-verifies the 17,697-ply game, re-runs the full invariant corpus and all
32 CP-SAT decisions, and byte-compares the result against the committed
certificate; `solve_model.py` re-decides every shape by both methods and
fails on any disagreement. Two artefacts are cached across pytest runs in
`.pytest_cache`, keyed by content and source hashes so the caches
self-invalidate (first run ~6.5 s): the parsed reference game and the
compressed skeleton. On a solver-less install the CP-SAT tests skip
themselves.

## The one-line check

The whole result, replayed and judged in about a second:

```bash
make witness
```

```
plies              17697
termination        checkmate
critical segments  118
final fen          3k4/3Q4/4K3/8/8/8/8/8 b - - 150 8849
```

## The claims

Quick tier unless marked **full**. `pawns`, `blocks`, `invariant`,
`adversary` live under `src/long_chess/bound/`; `abstract`, `independent`
under `src/long_chess/model/`.

| Paper | Claim | Decided by | Pinned by |
|---|---|---|---|
| Lemma 2.4 (`lem:decomposition`) | `L = 150K − S − Σδ` closes exactly on the witness: `17697 = 150·118 − 3 − 0` | verifier + per-ply trace | `tests/test_known_game.py` |
| Lemma 3.1 (`lem:pawnbasics`) | ≤ 6 moves per pawn, `P ≤ 96` | `pawns.MAX_PAWN_MOVES` | `tests/test_bound.py::TestTerms` |
| Lemma 3.3 (`lem:cap10`) | unresolved origin pair ≤ 10, exhausted over a relaxation of chess | `pawns.check_origin_pair_cap` | `tests/test_bound.py::TestOriginPairCap` |
| Lemma 3.3 (attained) | 10 reached by a legal 24-ply sequence (any completion preserves it) | sequence replayed by python-chess | `tests/test_bound.py::TestOriginPairCap` |
| Lemma 3.3 (proof, first half) | two facing pawns never pass | `pawns.check_file_lemma` | `tests/test_bound.py::TestFileLemma` |
| Prop. 3.6 (`prop:pminuso`) | `P − O ≤ 88`, maximiser unique at `f = 8` | `pawns.pawn_minus_overlap_bound` | `tests/test_bound.py::TestPawnMinusOverlap` |
| Lemma 3.7 (`lem:ct30`) | `C + T ≤ 30`, both profiles reach it | `pawns.captures_plus_closing_bound` | `tests/test_bound.py::TestCapturesPlusClosing` |
| Thm. 3.8 (`thm:k118`) | `K = 118` admits exactly one term assignment | `pawns.equality_witnesses` | `tests/test_bound.py::TestEqualityConditions` |
| Thm. 4.5 (`thm:s3`), terminal-endpoint step | *deleting* the terminal endpoint never adds a switch — appending it never lowers the block count, and when it starts a new block it adds exactly one switch — all patterns ≤ 12 blocks | `blocks.check_dropping_terminal_endpoint_never_adds_a_switch` | `tests/test_bound.py::TestSwitchLowerBound` |
| Lemma 4.3 (`lem:homerank`), [H0] [H3] [H4] | finite obligations, settled exhaustively | `invariant.verify` | `tests/test_invariant.py` |
| Lemma 4.3, [H1] [H2] [H5] [H6] | rule axioms, corpus-checked against python-chess | `invariant.verify` | `tests/test_invariant.py` (small corpus); the certificate records the full-size corpus on every `certify.py` run |
| Lemma 4.3 (adversarial) | seeded search: every legal attacker move at every visited position, 0 breaches, 0 en-passant offers | `adversary.audit` | `scripts/attack_lemma.py` (standalone, ~34 s) |
| Props. 4.1 / 4.2 / 4.4, Thm. 4.5 (`thm:s3`) | the five critical-move patterns a game with `S ≤ 2` could have, all refuted; refusal to close if any survives (`W B W` is not one of them — see [which patterns, and whose](#which-patterns-and-whose)) | `blocks.switch_lower_bound` | `tests/test_bound.py::TestSwitchLowerBound`, `scripts/analyse_bound.py` (0.1 s) |
| Remark 4.6 (`rem:notglobal`) | `S ≥ 3` is conditional on `K = 118`: the 16-ply knight shuffle has `K = 1, S = 0` | verifier | `tests/test_bound.py::TestSwitchThreeIsNotGlobal` |
| Cor. 5.3 (`cor:exact`) | bound attained: the witness is legal, 17,697 plies, mate | `long_chess.verifier` | `tests/test_known_game.py`, `make witness` |
| App. A | clock < 150 before every non-final ply; mate at exactly 150; no position occurs 3× (max multiplicity 2) | verifier trace | `tests/test_known_game.py`, `tests/test_termination.py` |
| App. A | a game ending in mate contains no dead position | legal suffix-to-mate argument; legality of the suffixes checked by the verifier | `tests/test_known_game.py` |
| App. A **full** | a distinct 17,697-ply game rebuilt from the skeleton, verified, diverging from the reference by the quoted 17,032 plies | `filler` + verifier via `scripts/certify.py` | `scripts/check_certificate.py`; the manifest's `game` block pins the divergence |
| App. B | the model accepts the real witness's exact assignment; verdicts and ablation pinned per pattern | `model.validate`, `model.abstract` | `tests/test_model.py` |
| App. B **full** | CP-SAT and the arithmetic checker agree on all 8 patterns × 2 endings; minimum feasible `S = 3`; the no-lemma column | `model.abstract`, `model.independent` | `scripts/solve_model.py` (fails on any disagreement), certificate `decisions` |
| App. B (audit record) | the three over-constraint instances cannot silently return | regression pins | `TestTheOldCapWasFalse`, `TestCheckmateBranchWasNotAModel`, `TestMatingSideIsTheLastEndpoint` in `tests/test_defects.py` |
| App. B **full** | every verdict above, regenerated from a clean checkout, matches the committed certificate byte for byte | `scripts/certify.py` | `scripts/check_certificate.py` (~15 s) |
| App. B (future work) | the move rules re-derived from the FIDE Laws in one C99 file — 0x88 mailbox, no allocation, no python-chess, and neither 17,697 nor 118 anywhere in the source | `checker/longest_check.c` | `scripts/check_movegen.py`, CI job `movegen` |
| App. B (future work) | perft against node counts published outside this project: 7 positions, 44 checks to depth 6 | `--perft-suite` | as above (CI runs depth 6; `make verify-movegen` depth 5) |
| App. B (future work) | 33 hand-written rule cases, each naming the article it pins (3.7d, 3.7e, 3.8b, 3.9, 5.1.1, 5.2.1, 5.2.2) | `--rule-cases` | as above |
| App. B (future work) | the Art. 5.2.2 material test agrees with python-chess over its whole finite domain — 5,103 inventories, exhaustive, not sampled | `--material-scan` | as above |
| App. B (future work) | the witness replayed by the second implementation: 17,697 plies, mate, 118 critical segments, and 17,698 trace rows byte-identical to the verifier's | `checker/longest_check.c --trace` + `cmp` | as above |
| App. B (future work) | every legal move at every one of the 17,698 positions of the game agrees with python-chess — 730,845 moves, identical | `--dump-moves` vs `scripts/dump_legal_moves.py` | as above |
| App. B (future work) | [H1] [H2] [H5] [H6] re-checked over a corpus the C walks for itself, which is what would take python-chess out of the trusted base of Lemma 4.3's rule axioms | `--corpus` | as above |
| App. B (future work) | gcc and clang builds produce identical results; the witness, the rule cases and the corpus run clean under `-fsanitize=address,undefined` | two-compiler matrix | CI job `movegen` |

**The paper does not yet claim any of the seven rows above.** The code is in the
repository, `make verify-movegen` runs it and CI runs it on every push, but
[paper/main.tex](paper/main.tex) has not been updated: Appendix B still lists the
move generation of python-chess as part of the trusted base, which is why the
rows are marked *future work* rather than `App. B`. When the manuscript is
revised, the sentence that changes is that one, and only that one — this is
**implementation** independence, not author independence. Both generators were
written by the same person from the same reading of the Laws, so Appendix B's
other trusted-base item, the summary of the FIDE termination rules, is not
reduced by any of it. [docs/movegen.md](docs/movegen.md) states the independence
criteria, the mutation experiments that measure what each check is actually
worth, and the limits.

The suite is 440 tests in ~5 s (solver installed; CP-SAT tests skip without
it). The certificate ([data/certificate/](data/certificate/)) records every
decision with a SHA-256 per artefact, including all 32 exported CP-SAT
models — with and without the home-rank constraint — so the UNSATs can be
re-run under any solver.

## Which patterns, and whose

Three different objects here are described by block patterns, and they are
deliberately not the same set — the paper refutes six, the direct checker five,
the model decides eight.

| Object | Patterns | Method | Role in the theorem |
|---|---|---|---|
| critical-move pattern | the six nonempty alternating patterns of ≤ 3 blocks: `B`, `W`, `B W`, `W B`, `B W B`, `W B W` | hand proof, Props. 4.1 / 4.2 / 4.4 | at least four critical-move blocks |
| critical-move pattern of a game with `S ≤ 2` | the five it can be: `B`, `W`, `B W`, `W B`, `B W B` | direct checker, `bound.blocks` | `S ≥ 3` |
| endpoint pattern | eight of ≤ 4 blocks × two endings | CP-SAT and the arithmetic checker, `model` | cross-check only |
| the witness's endpoint pattern | `B W B W` | verifier | attainment |

`W B W` missing from the second row is not a coverage hole. `S` counts the
virtual Black endpoint before ply 1, so as an *endpoint* pattern `W B W`
already has `S = 3`; and a game whose critical-move pattern is `W B W` has
endpoint pattern `W B W` or `W B W B`, so `S ≥ 3` either way. It cannot arise
under the hypothesis the direct checker runs under, and there is nothing there
for it to be refuted against. The paper's statement is the stronger one — the
critical-move pattern has at least four blocks, with no `S ≤ 2` hypothesis — so
it does need `W B W` refuted, and Prop. 4.4 kills both three-block patterns in
a single proof. The model decides it as well, from the other side.

## What is *not* claimed here

The mechanical checks do not constitute the proof, and they share one root
of trust: the move generation of python-chess (pinned version), used both by
the witness verifier and by the corpus checks of the rule axioms
[H1] [H2] [H5] [H6]. See the paper's Appendix B for the precise trusted
base, and [docs/](docs/) for the long-form audits behind Appendices A–B.

That paragraph states the paper's position, and it is still the paper's
position. In the repository the *future work* rows above put a second,
independently implemented generator behind the same checks; what they cannot
touch is the reading of the Laws both implementations were written from.
