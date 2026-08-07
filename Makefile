# Verification entry points. See CLAIMS.md for what each check establishes.

UV := uv run

.PHONY: witness verify lint paper

## The whole result in about a second: replay and judge the 17,697-ply game.
witness:
	$(UV) python -m long_chess.verifier data/longest.pgn \
	  --expect-plies 17697 --expect-termination checkmate

## Everything (~35 s): the witness, the counting proof, the test suite, the
## second move generator, and the CP-SAT cross-check.
##
## Two steps degrade rather than fail. Without a C compiler the move-generator
## checks skip; without OR-Tools (`uv sync --extra solver`) the CP-SAT
## cross-check skips. Both are cross-checks on a proof that stands without
## them, and a check that cries wolf gets disabled.
verify: witness
	$(UV) python scripts/analyse_bound.py
	$(UV) pytest -q
	$(UV) python scripts/check_movegen.py
	$(UV) python scripts/solve_model.py data/skeleton.json

lint:
	$(UV) ruff check .

## Rebuild the manuscript (needs tectonic or a TeX toolchain; see
## paper/README.md). SOURCE_DATE_EPOCH pins the PDF's embedded timestamps so
## the committed PDF reproduces byte for byte from a clean checkout.
paper:
	cd paper && SOURCE_DATE_EPOCH=0 tectonic main.tex
