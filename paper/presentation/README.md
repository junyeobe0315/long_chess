# Presentation slides

Talk decks for the paper, in two languages, plus a speaker script for each:

| file | what it is |
|---|---|
| `slides-en.tex` / `.pdf` | English deck, 34 numbered frames + 7 part dividers |
| `slides-ko.tex` / `.pdf` | Korean deck, same structure and the same figures |
| `slides-en-notes.tex` / `.pdf` | English speaker script (the `\note{}` blocks only) |
| `slides-ko-notes.tex` / `.pdf` | Korean speaker script |
| `longchess.sty` | `\usetheme{Madrid}` plus the content machinery: statement blocks, part dividers, figure vocabulary, colour aliases |
| `lcfigures.sty` | every diagram, one macro each |
| `make_assets.py` | regenerates `assets/` — segment data, board diagrams, screenshots |

Sized for a 40–50 minute seminar.

## How the decks are built

The furniture is beamer's stock **Madrid** theme — rounded blue title box,
tripartite footline, shadowed blocks — with nothing about it changed, and
beamer's default sans (via `lmodern`). `longchess.sty` adds only content
machinery on top; the palette names the diagrams use (`lcdark`, `lcpale`,
`lcmid`, `lcaccent`, `lcgreen`) are set to the theme's own colours, so the
pictures and the furniture agree without either being tuned to the other.
Both decks set short forms — `\title[…]`, `\author[…]`, `\institute[…]`,
`\date[…]` — because Madrid's footline uses them.

**The slides state the mathematics; the narration is in `\note{}`.** Each
content slide carries a definition, lemma, proposition or theorem —
written out, and numbered as in `main.tex` so a listener can find it in the
paper afterwards — beside the picture that explains it. The numbers are
typed by hand precisely because they must track the paper rather than the
slide order.

Three block flavours, following the stock blue themes:

| environment | used for | colour |
|---|---|---|
| `\begin{lcstate}{정의 2.1}{critical move}` | definitions, lemmas, propositions, remarks | blue |
| `\begin{lcthm}{정리 5.1}{상한}` | the theorems that carry the result | red |
| `\begin{lcproof}` + `\begin{lcsteps}` | proofs, as numbered steps | green |

Everything said out loud lives in `\note{}`, and the `-notes` wrappers are
two lines that re-typeset the same source with beamer's `notes=only`
option. So there is exactly one place to edit. The note pages carry a
thumbnail of their slide, which makes them usable as a rehearsal script on
their own.

Seven parts, deliberately different in kind — the structure is what keeps
storytelling, mathematics and engineering from being argued at once on one
slide:

| part | content | mode |
|---|---|---|
| 0. Origin | the Ing Chess video, Labelle's page, "I believe" | story |
| I. Rules | 2014, the halfmove clock, a century of partial answers | background |
| II. Counting | `L = 150K − S − Σδ`, `K ≤ 118` | mathematics only |
| III. Switches | the six patterns, the home-rank lemma, `S ≥ 3` | mathematics only |
| IV. Search | the two attacks that failed | engineering only |
| V. Checking | the verifier, the two cross-checks | engineering only |
| VI. Meaning | the real game, A048987, open directions | significance |

Both decks share `longchess.sty` and `lcfigures.sty`, so a figure is drawn
once. Labels inside figures go through the `\lcs*` macros, which default to
English; `slides-ko.tex` renames them in one block near the top. Adding a
word to a figure means adding a `\lcstring` default in `longchess.sty` and
a `\renewcommand` in `slides-ko.tex` — never Korean text inside
`lcfigures.sty`.

## Build

```bash
tectonic slides-en.tex
tectonic slides-ko.tex
tectonic slides-en-notes.tex
tectonic slides-ko-notes.tex
```

The Korean deck uses `xeCJK` with the **Noto Sans KR** font (kotex's
`xetexko` needs an ICU line-break locale that tectonic does not ship). If
the font is missing:

```bash
mkdir -p ~/.local/share/fonts
curl -sL -o ~/.local/share/fonts/NotoSansKR-Regular.otf \
  https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/KR/NotoSansKR-Regular.otf
curl -sL -o ~/.local/share/fonts/NotoSansKR-Bold.otf \
  https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/KR/NotoSansKR-Bold.otf
fc-cache -f
```

## Assets

```bash
uv run --with cairosvg --with playwright --with pymupdf python make_assets.py
uv run --with cairosvg python make_assets.py --no-net   # boards and data only
```

`make_assets.py` writes `assets/` and needs no arguments. Everything in it
is derived, not drawn by hand:

- **`segments.tex`** — the reference game's real segment structure, read
  back by `lcfigures.sty`. Replaying `data/longest.pgn` gives 118
  segments, their endpoint colours (`B×10, W×49, B×50, W×9` — the `BWBW`
  of Corollary 5.2), the kind of critical move ending each (96 pawn moves,
  29 captures, 8 overlaps, 1 closing segment) and the three segments of
  length 149, which fall at positions 11, 60 and 110 — exactly the block
  boundaries. The big diagram on the last part's opening slide is
  therefore a picture of the actual game; it cannot drift from the paper.
- **board diagrams** — positions replayed from the same PGN and from the
  move sequences the paper quotes, rendered to vector PDF by
  python-chess, with the talk's own highlighting (the wall of pawns in the
  home-rank lemma, the file an unresolved origin pair is locked on). Same
  pipeline and same licensing as [`../figures/`](../figures/README.md):
  the piece images are Colin M. L. Burnett's, used under the BSD option of
  their triple licence.
- **screenshots** — the pages the talk cites.

### Screenshots are third-party material

`shot-labelle.png`, `shot-augment.png`, `shot-sigbovik.png`,
`shot-yt-short.jpg` and `shot-yt-video.jpg` are captures of, respectively,
[wismuth.com](https://wismuth.com/chess/longest-game.html),
[augmentchess.org](https://augmentchess.org/), the first page of
[Murphy's SIGBOVIK paper](http://tom7.org/chess/longest.pdf), and the
YouTube thumbnails of the two videos that started the project. They are
shown to identify and credit the sources on screen, each captioned with
its origin, which is ordinary practice for a talk — but they are not this
repository's to license, and the judgement about showing them is the
speaker's. `make_assets.py` re-fetches all of them, so the decks can be
rebuilt from a checkout that does not carry them: every slot goes through
`\lcshot`, which draws a labelled placeholder when the file is absent
rather than failing the build.

## Adding a slide

Keep one idea per slide, and keep the mode of its part. If a slide needs
more than a formula, a figure and a caption, the extra belongs in its
`\note{}`. New diagrams go in `lcfigures.sty` as a single `\fig*` macro so
both decks get them at once.

Four things to know about the layout, all learned the hard way. The first
three produce errors that name neither the file nor the construct at
fault, so they are worth recognising on sight:

- Coordinates are evaluated by pgfmath in TeX dimensions, which overflow
  above **16384**. `17697` in a coordinate is an error; `\figscale` and
  `\figoeis` work in units of a hundred plies for that reason.
- A `\\` **nested inside a group** in a TikZ node with `align=…` breaks the
  node's line-breaking machinery — `\textcolor{…}{a\\b}` is the trap. Put
  the `\\` at the outer level and colour each line separately. The symptom
  is an undefined `\tikzscope@linewidth` reported from an unrelated path.
- A line inside a `\node` argument must never end in a lone backslash.
- The frame furniture in `longchess.sty` wraps every horizontal item in an
  `\hbox`. A bare `\hspace*` in one of those templates forces horizontal
  mode and turns the next `\nointerlineskip` into `You can't use
  \prevdepth in horizontal mode`.

Board images are tinted to the palette by `make_assets.py` (`BOARD_COLORS`);
python-chess's default brown board clashes with the blue deck.
