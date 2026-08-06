# Verification entry points for the companion repository.
# See CLAIMS.md for what each target establishes and the measured runtimes.

UV := uv run

.PHONY: witness verify-quick verify-full lint paper

## The whole result in about a second: replay and judge the 17,697-ply game.
witness:
	$(UV) python -m long_chess.verifier data/longest.pgn \
	  --expect-plies 17697 --expect-termination checkmate

## Quick tier (no solver needed, ~10 s): the counting proof, the witness,
## and the test suite.
verify-quick: witness
	$(UV) python scripts/analyse_bound.py
	$(UV) pytest -q

## Full tier (~20 s): quick, plus the CP-SAT/arithmetic cross-checks over
## every shape and both endings, and the byte-for-byte certificate
## reproduction — which repacks and re-verifies the 17,697-ply game and
## re-runs the full invariant corpus on every invocation.
## Needs: uv sync --frozen --extra solver
verify-full: verify-quick
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
