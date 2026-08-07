# The paper

`main.tex` is the manuscript — the main artifact this repository exists
to support. The committed `main.pdf` is its build output, kept so the
paper is readable without a TeX toolchain; regenerate it after any edit.

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

`make paper`, from the repository root, builds with
`SOURCE_DATE_EPOCH=0`, which pins the PDF's embedded timestamps: the
committed PDF reproduces byte for byte from a clean checkout.

## Figures

The board diagrams under `figures/` are committed and regenerable:

```bash
uv run --with cairosvg python paper/figures/make_figures.py
```

The script replays the exact move sequences quoted in the paper, so the
figures cannot drift from the text. The piece images embedded in the
output are Colin M. L. Burnett's, used under the BSD option of their
triple licence — see [figures/README.md](figures/README.md).

## Slides

[presentation/](presentation/) holds beamer decks for the paper, in
English and Korean; its README has the build notes.
