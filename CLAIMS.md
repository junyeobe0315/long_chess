# Claims map

Every machine-checked claim of the paper ([paper/main.pdf](paper/main.pdf)),
mapped to the code that decides it and the test that pins it. Statement
numbers refer to the current draft; the `\label` names in
[paper/main.tex](paper/main.tex) are the stable identifiers.

**The paper's proof is a hand argument and is checkable without running
anything here.** What this repository adds is the finite case analyses
exhausted mechanically, the witness verified ply by ply, and the central case
analysis re-decided by two further methods.

`pawns`, `blocks`, `invariant`, `adversary` live under
`src/long_chess/bound/`; `abstract`, `independent` under
`src/long_chess/model/`.

| Paper | Claim | Decided by | Pinned by |
|---|---|---|---|
| Lemma 2.4 (`lem:decomposition`) | `L = 150K − S − Σδ` closes exactly on the witness: `17697 = 150·118 − 3 − 0` | verifier + per-ply trace | `tests/test_known_game.py` |
| Lemma 3.1 (`lem:pawnbasics`) | ≤ 6 moves per pawn, `P ≤ 96` | `pawns.MAX_PAWN_MOVES` | `tests/test_bound.py::TestTerms` |
| Lemma 3.3 (`lem:cap10`) | unresolved origin pair ≤ 10, exhausted over a relaxation of chess; 10 attained by a legal 24-ply sequence | `pawns.check_origin_pair_cap`, `pawns.check_file_lemma` | `tests/test_bound.py::TestOriginPairCap`, `::TestFileLemma` |
| Prop. 3.6 (`prop:pminuso`) | `P − O ≤ 88`, maximiser unique at `f = 8` | `pawns.pawn_minus_overlap_bound` | `tests/test_bound.py::TestPawnMinusOverlap` |
| Lemma 3.7 (`lem:ct30`) | `C + T ≤ 30`, both profiles reach it | `pawns.captures_plus_closing_bound` | `tests/test_bound.py::TestCapturesPlusClosing` |
| Thm. 3.8 (`thm:k118`) | `K = 118` admits exactly one term assignment | `pawns.equality_witnesses` | `tests/test_bound.py::TestEqualityConditions` |
| Lemma 4.3 (`lem:homerank`) | [H0] [H3] [H4] finite obligations settled exhaustively; [H1] [H2] [H5] [H6] are rule axioms, corpus-checked against both move generators | `invariant.verify`, `adversary.audit` | `tests/test_invariant.py`, `scripts/attack_lemma.py` |
| Props. 4.1 / 4.2 / 4.4, Thm. 4.5 (`thm:s3`) | every critical-move pattern a game with `S ≤ 2` could have is refuted, and the terminal-endpoint step holds over all patterns ≤ 12 blocks | `blocks.switch_lower_bound`, `blocks.check_dropping_terminal_endpoint_never_adds_a_switch` | `tests/test_bound.py::TestSwitchLowerBound`, `scripts/analyse_bound.py` |
| Cor. 5.3 (`cor:exact`) | bound attained: the witness is legal, 17,697 plies, mate; clock < 150 before every non-final ply; no position occurs 3× | `long_chess.verifier` | `tests/test_known_game.py`, `tests/test_termination.py`, `make witness` |
| App. B | CP-SAT and the arithmetic checker agree on all 8 endpoint patterns × 2 endings; minimum feasible `S = 3`; the model accepts the witness's own assignment | `model.abstract`, `model.independent`, `model.validate` | `tests/test_model.py`, `scripts/solve_model.py` (fails on any disagreement) |
| App. A / B | the rules re-derived from the Laws in one C99 file — no python-chess, and neither 17,697 nor 118 in the source — replays the witness to the same verdict and byte-identical trace, and its own generation is checked against externally published perft counts and hand-written rule cases | `checker/longest_check.c` | `scripts/check_movegen.py`, CI job `movegen` |

The three over-constraint instances repaired during this work cannot silently
return: `TestTheUnresolvedPairCapWasFalse`, `TestCheckmateBranchWasNotAModel`,
`TestMatingSideIsTheLastEndpoint` in `tests/test_defects.py`.

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
under the hypothesis the direct checker runs under. The paper's statement is
the stronger one — the critical-move pattern has at least four blocks, with no
`S ≤ 2` hypothesis — so it does need `W B W` refuted, and Prop. 4.4 kills both
three-block patterns in a single proof.

## What is *not* claimed

The mechanical checks do not constitute the proof. Their root of trust is not
a single library: the witness verification and the rule-axiom corpora
[H1] [H2] [H5] [H6] run under two independently implemented move generators —
python-chess (pinned in `uv.lock`) and
[`checker/longest_check.c`](checker/longest_check.c) — so what remains is the
proposition that the two do not fail identically, together with the reading of
the FIDE Laws that both were written from. This is **implementation**
independence, not author independence.
[docs/verification.md](docs/verification.md) states the independence criteria,
the mutation experiments that measure what each check is actually worth, and
the limits.
