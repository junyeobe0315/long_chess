# Where the data came from

Two of these files are not ours. They are included so the results can be
reproduced without a network round-trip, and both are attributed here and in
the code that reads them. **They are excluded from the repository's MIT
license**: both are Tom Murphy VII's published artefacts, redistributed here
with attribution as factual game data (a game score records moves, not
expression); the originals remain at the URLs below.

## Third-party

**`longest.pgn`** — the 17,697-ply game, by Tom Murphy VII, published at
<http://tom7.org/chess/longest.pgn> alongside *Is this the longest chess game?*
(SIGBOVIK 2020). `sha256 6700b7b7…680bb`, pinned in
`tests/test_known_game.py`. Re-fetch with `scripts/fetch_reference.py`.

Note it is not in his repository — `longest.cc` writes it at run time — so the
copy on his site is the artefact.

**`skeleton_reference.txt`** — the 289-ply critical skeleton, lifted out of
`longest.cc` in the same author's SourceForge tree
([`trunk/chess/longest.cc`](https://sourceforge.net/p/tom7misc/svn/HEAD/tree/trunk/chess/longest.cc)),
where it lives as a raw string. Careful: the file defines `slowgame_pgn` twice
and the second assignment, marked `// XXX`, is a 22-move experiment. This is
the first one, the 145-move skeleton that actually produced the published game.

It is here because our cycle cancellation is checked against it, and agreeing
with an independently produced artefact is worth more than agreeing with
ourselves. Not regenerable offline.

## Ours, and regenerable

| file | made by |
|---|---|
| `skeleton.json`, `skeleton.pgn` | `scripts/extract_skeleton.py data/longest.pgn` |

The per-ply verification trace (`longest.trace.tsv`, 1.5 MB) is gitignored
derived data; regenerate it with

```bash
uv run python -m long_chess.verifier data/longest.pgn --trace data/longest.trace.tsv
```

`scripts/check_movegen.py` regenerates it for itself when it is absent, which
is the stronger check anyway: it compares the C implementation against what
python-chess says *now*, not against a file that happened to be lying around.
