# Verification entry points for the companion repository.
# See CLAIMS.md for what each target establishes and the measured runtimes.

UV := uv run

.PHONY: witness verify-quick verify-movegen verify-full lint paper

## The whole result in about a second: replay and judge the 17,697-ply game.
witness:
	$(UV) python -m long_chess.verifier data/longest.pgn \
	  --expect-plies 17697 --expect-termination checkmate

## Quick tier (no solver needed, ~10 s): the counting proof, the witness,
## and the test suite.
verify-quick: witness
	$(UV) python scripts/analyse_bound.py
	$(UV) pytest -q

## The second move generator (~20 s): builds checker/longest_check.c and runs
## perft against published node counts, the hand-written FIDE rule cases, the
## obligation corpus, and the two differentials against the python-chess side —
## the per-ply trace and the complete legal-move set at every position of the
## witness. Needs a C compiler; without one it skips and returns 0, the way the
## CP-SAT tests skip without OR-Tools. See checker/README.md and docs/movegen.md.
verify-movegen:
	$(UV) python scripts/check_movegen.py

## Full tier (~45 s): quick, plus the second move generator, the CP-SAT/
## arithmetic cross-checks over every shape and both endings, and the
## byte-for-byte certificate reproduction — which repacks and re-verifies the
## 17,697-ply game and re-runs the full invariant corpus on every invocation.
## Needs: uv sync --frozen --extra solver
verify-full: verify-quick verify-movegen
	uv run --extra solver python scripts/solve_model.py data/skeleton.json
	uv run --extra solver python scripts/check_certificate.py \
	  data/skeleton.json data/certificate

lint:
	$(UV) ruff check .

## Rebuild the manuscript (needs tectonic or a TeX toolchain; see
## paper/README.md). SOURCE_DATE_EPOCH pins the PDF's embedded timestamps so
## the committed PDF reproduces byte for byte from a clean checkout.
paper:
	cd paper && SOURCE_DATE_EPOCH=0 tectonic main.tex
