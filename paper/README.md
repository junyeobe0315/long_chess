# The paper

`main.tex` is the manuscript — the main artifact this repository exists to
support. **Status: full first draft, not yet submitted anywhere.** The
committed `main.pdf` is its build output, kept so the draft is readable
without a TeX toolchain; regenerate it after any edit.

## Build

Any of:

```bash
tectonic main.tex
```

```bash
latexmk -pdf main.tex
```

Plain `pdflatex main.tex` twice also works — the bibliography is inline
(`thebibliography`), so no BibTeX pass is needed.

The board diagrams under `figures/` are committed and regenerable:

```bash
uv run --with cairosvg python paper/figures/make_figures.py
```

The script replays the exact move sequences quoted in the paper, so the
figures cannot drift from the text.

## Where the paper's content came from, and what follows

This is the phase-0 deliverable of the paper-first restructuring: the proof
moves out of the repository's front matter and into a citable manuscript.
The map below records which existing document fed which section. Phases
1–4 have since executed — README inverted to a companion front page, the
claims map at [/CLAIMS.md](../CLAIMS.md), `make` verification targets, and
docs/ reorganised: the proof documents carry banners tying them to paper
sections, and the development-history documents were removed outright when
the repository history was squashed for publication.

| Source in this repository | Paper section | Later phase |
|---|---|---|
| `README.md` — result, "proof in nine lines", decomposition, "why each step holds" | §1 Introduction, §2–§5 | README shrinks to a companion-repo front page pointing here |
| `docs/optimality.md` — "The chain" (steps 1–9) | §2 Setting, §3 K ≤ 118, §5 Main theorem | replace body with a pointer to the paper; keep the file as the repo-side index |
| `docs/optimality.md` — "Killing the five shapes" | §4 Propositions 4.2–4.5 | same |
| `docs/optimality.md` — both correction sections, `abstract-model.md` correction | §7.3 Corrections | keep full versions in docs/ as the long-form record |
| `docs/optimality.md` — "Attacking the home-rank lemma" | §7.1 Finite checks (adversarial search paragraph) | keep; the numbers live in the certificate |
| `src/long_chess/bound/invariant.py` docstring — the H0–H6 induction | §4 Lemma 4.4 (home-rank lemma) | docstring stays but defers to the paper as the canonical statement |
| `docs/abstract-model.md` — the model, constraint audit, endpoint convention | §7.2 Cross-checks (summary) | keep in docs/ as the detailed audit |
| `docs/dead-positions.md` | §6 (mate-tail argument), §7.4 trusted base | keep |
| `docs/segment-independence.md` | §6 one sentence (rebuilt witness) | keep — construction detail, not proof |
| development records (fixed-multiset switch bound; padding capacity) | not in the paper | removed — development history, superseded by the paper and the repository's checks |
| `README.md` — "Decided three times" table | §7.2 | README keeps only the pointer |
| `README.md` — "Traps" | §7.4, briefly | keep in docs/ |
| certificate + verifier runs | §6 witness facts, Appendix A | unchanged; Appendix A is the claims map phases 1–2 formalise as `CLAIMS.md` |

## Release sequence (phase 5)

Done already: `LICENSE`, `CITATION.cff` (version 1.0.0, released
2026-08-07; DOI placeholder commented with its trigger), package metadata
at 1.0.0, the paper dated and citing tag `v1.0.0`, the annotated tag
`v1.0.0` created locally, and the PDF built reproducibly
(`SOURCE_DATE_EPOCH=0`, byte-identical across builds). The rest, in
order, each at its trigger:

1. **Repository goes public** → enable the Zenodo–GitHub integration
   toggle (must precede the tag), then Software Heritage "Save Code Now".
2. **Manuscript ready for arXiv** → cut annotated tag `v1.0.0` + GitHub
   release; Zenodo automatically archives it and mints a version DOI and
   a concept DOI.
3. **Fill the placeholders — none may survive into a submitted version.**
   The paper's `\cite{repo}` entry cites the **version DOI** plus tag and
   commit SHA: this paper claims byte-exact reproducibility, so the
   citation should pin the exact release, not the moving concept DOI.
   (`CITATION.cff` keeps the concept DOI — the right identifier for the
   software as an evolving whole — plus `version`/`date-released`; the
   root README's archival table gets both.) If waiting for Zenodo would
   hold up submission, arXiv v1 may cite "tag `v1.0.0`, commit `<SHA>`"
   alone and the DOI can be added in an arXiv replacement (v2) — arXiv
   prefers replacements over new submissions for revisions. At the same
   time set `\date{}` to the submission date and drop the "Draft of"
   prefix. Recompile, commit.
4. **Submit to arXiv** (Comments field: companion repository URL + DOI).
   Do **not** put the repository's Zenodo DOI in arXiv's DOI metadata
   field — that field is for a journal DOI of the *paper itself*; the
   repository DOI belongs in the references and the Comments field. Once
   posted, add the arXiv ID to the root README and to
   `preferred-citation` in `CITATION.cff` (template commented in place).

## Open items before submission

- [x] Title: "The maximum length of a chess game under the FIDE Laws is
      17,697 plies".
- [x] Affiliation: Department of Applied Mathematics, Kongju National
      University (official English name per the university's department
      listing), with an independence statement in the acknowledgements.
- [x] Related work: Labelle's page is the primary prior source — the 118
      count, the three-switch schedules and the conjecture — cited in the
      abstract, §1 and the acknowledgements; Murphy and Tromp positioned
      around it.
- [ ] arXiv submission is blocked on an endorsement for math.CO; the README
      links the in-repo PDF until it clears.
- [x] Repository tag `v1.0.0` + Zenodo DOIs pinned: the paper cites the
      version DOI 10.5281/zenodo.21828026; `CITATION.cff` carries the
      concept DOI 10.5281/zenodo.21828025.
- [ ] Consider a second, independently implemented move generator for the
      witness verification, and upgrade §7.3(ii) accordingly.
- [ ] arXiv metadata: math.CO primary, cs.DM cross-list; ancillary files
      (witness PGN + a self-contained checker) per the Gardam pattern.
- [ ] A careful proofread of §2–§4 against `docs/optimality.md` by a reader
      who has not seen either.
