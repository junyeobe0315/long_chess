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
| **full** | `uv sync --frozen --extra solver` (adds CP-SAT) | `make verify-full` | ~20 s |

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
| Lemma 4.1 (`lem:seam`) | terminal endpoint never adds a switch, all shapes ≤ 12 blocks | `blocks.check_terminal_endpoint_free` | `tests/test_bound.py::TestSwitchLowerBound` |
| Lemma 4.4 (`lem:homerank`), [H0] [H3] [H4] | finite obligations, settled exhaustively | `invariant.verify` | `tests/test_invariant.py` |
| Lemma 4.4, [H1] [H2] [H5] [H6] | rule axioms, corpus-checked against python-chess | `invariant.verify` | `tests/test_invariant.py` (small corpus); the certificate records the full-size corpus on every `certify.py` run |
| Lemma 4.4 (adversarial) | seeded search: every legal attacker move at every visited position, 0 breaches, 0 en-passant offers | `adversary.audit` | `scripts/attack_lemma.py` (standalone, ~34 s) |
| Props. 4.2 / 4.3 / 4.5, Thm. 4.6 (`thm:s3`) | all five `S ≤ 2` shapes refuted; refusal to close if any survives | `blocks.switch_lower_bound` | `tests/test_bound.py::TestSwitchLowerBound`, `scripts/analyse_bound.py` (0.1 s) |
| Remark 4.7 (`rem:notglobal`) | `S ≥ 3` is conditional on `K = 118`: the 16-ply knight shuffle has `K = 1, S = 0` | verifier | `tests/test_bound.py::TestSwitchThreeIsNotGlobal` |
| Thm. 5.1 (`thm:main`) | bound attained: the witness is legal, 17,697 plies, mate | `long_chess.verifier` | `tests/test_known_game.py`, `make witness` |
| §6 | clock < 150 before every non-final ply; mate at exactly 150; no position occurs 3× (max multiplicity 2) | verifier trace | `tests/test_known_game.py`, `tests/test_termination.py` |
| §6 | a game ending in mate contains no dead position | legal suffix-to-mate argument; legality of the suffixes checked by the verifier | `tests/test_known_game.py` |
| §6 **full** | a distinct 17,697-ply game rebuilt from the skeleton, verified, diverging from the reference by the quoted 17,032 plies | `filler` + verifier via `scripts/certify.py` | `scripts/check_certificate.py`; the manifest's `game` block pins the divergence |
| §7.2 | the model accepts the real witness's exact assignment; verdicts and ablation pinned per shape | `model.validate`, `model.abstract` | `tests/test_model.py` |
| §7.2 **full** | CP-SAT and the arithmetic checker agree on all 8 shapes × 2 endings; minimum feasible `S = 3`; the no-lemma column | `model.abstract`, `model.independent` | `scripts/solve_model.py` (fails on any disagreement), certificate `decisions` |
| App. B | the three over-constraint instances cannot silently return | regression pins | `TestTheOldCapWasFalse`, `TestCheckmateBranchWasNotAModel`, `TestMatingSideIsTheLastEndpoint` in `tests/test_defects.py` |
| §7 / App. A **full** | every verdict above, regenerated from a clean checkout, matches the committed certificate byte for byte | `scripts/certify.py` | `scripts/check_certificate.py` (~15 s) |

The suite is 437 tests in ~5 s (solver installed; CP-SAT tests skip without
it). The certificate ([data/certificate/](data/certificate/)) records every
decision with a SHA-256 per artefact, including all 32 exported CP-SAT
models — with and without the home-rank constraint — so the UNSATs can be
re-run under any solver.

## What is *not* claimed here

The mechanical checks do not constitute the proof, and they share one root
of trust: the move generation of python-chess (pinned version), used both by
the witness verifier and by the corpus checks of the rule axioms
[H1] [H2] [H5] [H6]. See the paper's §7.3 for the precise trusted base, and
[docs/](docs/) for the long-form audits behind §7.
