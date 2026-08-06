# long_chess

[![tests](https://github.com/junyeobe0315/long_chess/actions/workflows/tests.yml/badge.svg)](https://github.com/junyeobe0315/long_chess/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.13-blue)
![longest game](https://img.shields.io/badge/longest%20game-17%2C697%20ply-brightgreen)
![upper bound](https://img.shields.io/badge/upper%20bound-17%2C697%20ply-brightgreen)
![reviewed](https://img.shields.io/badge/peer%20reviewed-no-orange)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21828025.svg)](https://doi.org/10.5281/zenodo.21828025)

Companion repository for the paper

> **The maximum length of a chess game under the FIDE Laws is 17,697
> plies** — Junyeop Yim.
> Draft PDF: [paper/main.pdf](paper/main.pdf) · source: [paper/](paper/)
> An arXiv link will be added here once the submission clears
> (endorsement for math.CO pending).

**The proof lives in the paper.** Tom Murphy VII built a 17,697-ply legal
game ([SIGBOVIK 2020](https://tom7.org/chess/longest.pdf)) and left open
whether the arithmetic ceiling of 17,699 is reachable. The paper proves it
is not: no legal chess game exceeds 17,697 plies, so the constructed game
is longest possible.

This repository is the paper's supporting evidence. It mechanically checks
every finite case analysis the paper appeals to, verifies the 17,697-ply
witness move by move under an independent implementation of the
termination rules, re-decides the paper's central case analysis by two
further mechanical methods (CP-SAT and a solver-free arithmetic checker),
and packages every verdict into a byte-for-byte reproducible certificate.

## Verify

The whole result, replayed and judged in about a second:

```bash
make witness
```

Everything that runs without a constraint solver — the counting proof, the
witness, the test suite (~8 s):

```bash
make verify-quick
```

Everything: quick, plus the cross-checks over every block shape under both
endings and the byte-for-byte certificate reproduction, which repacks and
re-verifies the whole game (`uv sync --frozen --extra solver` first;
~20 s):

```bash
make verify-full
```

**[CLAIMS.md](CLAIMS.md)** maps each statement of the paper to the code
that decides it, the test that pins it, and the measured runtime.

## Layout

```
paper/                     the manuscript (main artifact)
CLAIMS.md                  paper statement -> code -> test map
src/long_chess/verifier/   independent FIDE judge; imports nothing else here
src/long_chess/bound/      the finite checks behind the proof's lemmas
src/long_chess/model/      CP-SAT + arithmetic cross-checks (paper S7.2)
src/long_chess/skeleton/   critical-segment representation of the witness
src/long_chess/filler/     rebuilds a distinct 17,697-ply game
src/long_chess/search/     critical-event scheduling analysis
tests/                     the ~5 s suite; every claim in CLAIMS.md is pinned here or in the scripts it names
scripts/                   one entry point per check; see CLAIMS.md
data/                      witness, skeletons, certificate (provenance: data/README.md)
docs/                      long-form audits behind the paper's S7; docs/README.md is the index
```

`verifier/` deliberately depends on nothing else in the package: a move
sequence counts as a result only when this judge passes it, and a judge
sharing code with the search would not be independent evidence.

## Status and trust

This is our own formalisation, machine-assisted and not yet peer reviewed.
What a sceptical reader must trust is stated precisely in the paper's
S7.3: the summary of the FIDE termination rules, and — for the mechanical
checks only — the move generation of
[python-chess](https://python-chess.readthedocs.io/en/latest/core.html)
(version pinned in `uv.lock` and recorded in the certificate). The paper's
Appendix B records three over-constraint instances repaired during this
work, each pinned by a regression test; the long-form audits live in
[docs/](docs/).

## Citing and archival status

Cite the **paper**, not the repository; [CITATION.cff](CITATION.cff)
carries this preference machine-readably, and GitHub's "Cite this
repository" button reads it. The placeholders below are each filled at a
fixed trigger point (the full release sequence is in
[paper/README.md](paper/README.md)):

| artefact | status | detail |
|---|---|---|
| arXiv link | **pending** | added once the math.CO endorsement clears and the preprint posts |
| `v1.0.0` tag + GitHub release | done | [v1.0.0](https://github.com/junyeobe0315/long_chess/releases/tag/v1.0.0) |
| Zenodo DOI | done | concept [10.5281/zenodo.21828025](https://doi.org/10.5281/zenodo.21828025) · v1.0.0 [10.5281/zenodo.21828026](https://doi.org/10.5281/zenodo.21828026) |
| Software Heritage SWHID | **pending** | "Save Code Now" at https://archive.softwareheritage.org/save/ |

## License

The repository's own code, documentation and generated data are
[MIT-licensed](LICENSE). Three exceptions: `data/longest.pgn` and
`data/skeleton_reference.txt` are Tom Murphy VII's published artefacts,
redistributed with attribution (see [data/README.md](data/README.md)); the
manuscript under [paper/](paper/) is not covered by the code license — its
license is chosen at arXiv submission; and the board-diagram PDFs under
`paper/figures/` embed piece images by Colin M. L. Burnett
(GFDL/BSD/GPL), used under the BSD option — see
[paper/figures/README.md](paper/figures/README.md).

## Attribution

`data/longest.pgn` and `data/skeleton_reference.txt` are Tom Murphy VII's —
the published game and the skeleton inside
[`longest.cc`](https://sourceforge.net/p/tom7misc/svn/HEAD/tree/trunk/chess/longest.cc)
respectively. They are included so the results reproduce offline;
[data/README.md](data/README.md) says exactly what came from where.

## References

- Murphy VII, [*Is this the longest chess game?*](https://tom7.org/chess/longest.pdf) (SIGBOVIK 2020)
- [FIDE Laws of Chess](https://handbook.fide.com/chapter/e012023), Articles 5.2.2, 9.6.1, 9.6.2
- Tromp, [*The longest chess game*](https://tromp.github.io/chess/longest.html) (summary note)
- [python-chess](https://python-chess.readthedocs.io/en/latest/core.html) ·
  [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver)
