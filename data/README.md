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
| `certificate/` | `scripts/certify.py data/skeleton.json -o data/certificate` |

`certificate/longest.pgn` is a *different* 17,697-ply game from the reference —
same skeleton, filler packed from scratch, 17,032 of its plies differ (665
agree). The
per-ply trace and the batch outputs under `m3/` are gitignored; regenerate them
with `scripts/certify.py` and `scripts/generate_games.py`.

### Reading the certificate

| file | what it answers |
|---|---|
| `certificate.json` | everything, including *when* and *from what* — timestamp, commit, tree hash, dependency versions, input hashes, solver parameters |
| `manifest.json` | only what a re-run must reproduce — the claim, the bound terms, the counting proof, all 16 decisions, and a SHA-256 for every artefact. No timestamp and no provenance, so it compares byte for byte from any commit |
| `longest.trace.tsv` | the per-ply verification log. **Gitignored** — 1.5MB, and regenerable — so a fresh clone has its hash but not the file. Both files name it under `artefacts_not_committed` |
| `models/<ending>/<shape>.pb.txt` | the CP-SAT model itself — one per shape per ending, plus a `.no-lemma` variant of each — so both the UNSATs and the no-lemma column can be re-run with any solver |

`certify.py` refuses to run from a dirty worktree: a commit SHA recorded beside
artefacts built from uncommitted code is a lie a reader has no way to detect.
`--allow-dirty` overrides it and records `worktree_clean: false`.

Check the committed certificate against a fresh run:

```bash
uv run --extra solver python scripts/check_certificate.py data/skeleton.json data/certificate
```

Set `SOURCE_DATE_EPOCH` to pin the timestamp in `certificate.json` too, and the
whole directory becomes reproducible byte for byte.

`certificate.json`'s `source_commit` points at the commit that produced it,
which is the commit *before* the certificate itself was added — the certificate
is an artefact of the source, not part of it.
