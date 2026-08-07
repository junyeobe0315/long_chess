#!/usr/bin/env python3
"""Build the optimality certificate — everything a third party needs.

    uv run --extra solver python scripts/certify.py data/skeleton.json \
        -o data/certificate

Produces a directory holding the game, its per-ply verification log, the two
independent decisions of the S ≤ 2 question, and the solver models themselves —
one per shape *and per ending*, with and without the home-rank lemma — so both
the UNSAT and the no-lemma column can be re-run by anyone with any CP-SAT.

What this is not: a machine-checkable proof object. CP-SAT does not emit one for
UNSAT. What replaces it is twofold — the counting proof in `long_chess.bound`,
which refutes every S ≤ 2 shape with no solver at all, and the arithmetic
cross-check in `long_chess.model.independent`, which decides the same question
by a different route and agrees on every shape.

Provenance is checked, not asserted. The run refuses to start from a dirty
worktree, because recording a clean commit SHA beside artefacts built from
uncommitted code is a lie a reader has no way to detect. ``--allow-dirty``
overrides it and says so in the certificate.

Two files come out with the numbers in them:

    certificate.json  the full record, including when it was produced
    manifest.json     the same minus anything that varies between runs, so a
                      re-run can be compared byte for byte

Set ``SOURCE_DATE_EPOCH`` to pin the timestamp in ``certificate.json`` too.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from long_chess.bound import (
    MAX_CAPTURABLE,
    MAX_CAPTURES,
    MAX_CAPTURES_DRAW,
    MAX_CAPTURES_PLUS_CLOSING,
    MAX_PAWN_MINUS_OVERLAP,
    MAX_PAWN_MOVES,
    MINIMUM_OVERLAPS,
    captures_plus_closing_bound,
    check_dropping_terminal_endpoint_never_adds_a_switch,
    check_file_lemma,
    check_home_rank_lemma,
    check_origin_pair_cap,
    critical_bound,
    ending_profiles,
    equality_conditions,
    pawn_minus_overlap_bound,
    ply_bound,
    refutations,
    switch_lower_bound,
    verify,
)
from long_chess.filler import pad_skeleton
from long_chess.model import (
    ENDINGS,
    all_shapes,
    analyse_independently,
    build,
    solve,
    validate,
)
from long_chess.skeleton import analyse, load, to_pgn
from long_chess.verifier import verify_game, write_tsv

SEGMENT_TARGET = 150
SOLVER_TIME_LIMIT = 60.0
"""Seconds per solve. Recorded because a shorter one could turn a decided
INFEASIBLE into an UNKNOWN, which `solve()` refuses to report as a refutation."""

PROVENANCE_INPUTS = ("uv.lock", "pyproject.toml")

NOT_COMMITTED = ("longest.trace.tsv",)
"""Artefacts hashed here but gitignored, so a fresh clone will not have them.

The per-ply trace is 1.5MB and regenerable from the PGN. Recording its hash is
still worth it — that is what pins the log — but a reader finding a hash with no
file behind it deserves to be told which file, and why, rather than left to
guess whether the certificate is broken.
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return None


def worktree_status() -> tuple[bool, str]:
    """Whether the tracked worktree is clean, and what is dirty if it is not."""
    status = git("status", "--porcelain")
    if status is None:
        return False, "not a git worktree"
    return (not status.strip()), status.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certify")
    parser.add_argument("skeleton", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="certify from a dirty worktree and record that it was dirty",
    )
    return parser


def produced_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), UTC).isoformat()
    return datetime.now(UTC).isoformat()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = args.output
    problems: list[str] = []

    # --- provenance, before anything is written ---------------------------
    clean, dirt = worktree_status()
    if not clean and not args.allow_dirty:
        print(
            "FAIL: the worktree is not clean, so a commit SHA recorded here "
            "would not describe the code that produced the artefacts:\n"
            f"{dirt}\n"
            "Commit first, or pass --allow-dirty to record it as dirty.",
            file=sys.stderr,
        )
        return 1

    commit = git("rev-parse", "HEAD") or "unknown"
    tree = git("rev-parse", "HEAD^{tree}") or "unknown"
    inputs = {
        name: sha256(Path(name)) for name in PROVENANCE_INPUTS if Path(name).exists()
    }
    inputs[str(args.skeleton)] = sha256(args.skeleton)

    out.mkdir(parents=True, exist_ok=True)

    # --- the game itself --------------------------------------------------
    skeleton = load(args.skeleton)
    padded, report = pad_skeleton(skeleton, seed=args.seed)
    if report.failures:
        print(f"FAIL: segments {report.failures} would not pack", file=sys.stderr)
        return 1

    result = verify_game(list(padded.moves), trace=True)
    stats = analyse(padded)
    print(f"game        {result.plies} ply, {result.termination.value}")

    (out / "longest.pgn").write_text(
        to_pgn(padded, Event="Longest legal chess game", Result="1-0"), encoding="utf-8"
    )
    with open(out / "longest.trace.tsv", "w", encoding="utf-8") as stream:
        write_tsv(result.trace, stream)
    (out / "skeleton.json").write_text(
        (args.skeleton).read_text(encoding="utf-8"), encoding="utf-8"
    )

    outcome = (result.plies, result.termination.value, stats.slack)
    if outcome != (17_697, "checkmate", 0):
        problems.append(f"the game is not a packed 17,697-ply mate: {result.plies}")

    # --- the bound, and the counting proof of S ≥ 3 -----------------------
    bound = critical_bound()
    envelope = pawn_minus_overlap_bound()
    equality = equality_conditions()
    lemmas = {
        "origin_pair_cap": dataclasses.asdict(check_origin_pair_cap()),
        # The record key is deliberately not renamed alongside the function:
        # it is the label of a committed artefact, and changing it would
        # invalidate every certificate produced before this line was written
        # for no gain — what the entry holds is `worst_increase <= 0`, which
        # names no direction to get backwards.
        "terminal_endpoint_free": dataclasses.asdict(
            check_dropping_terminal_endpoint_never_adds_a_switch()
        ),
        "file_lemma": dataclasses.asdict(check_file_lemma()),
        "home_rank_lemma": dataclasses.asdict(check_home_rank_lemma()),
        "invariant_obligations": [dataclasses.asdict(o) for o in verify()],
    }
    if not all(o["discharged"] for o in lemmas["invariant_obligations"]):
        problems.append("an invariant obligation is not discharged")
    print(f"bound       {bound.describe()}")
    print(f"equality    {equality.describe()}")

    try:
        switch = switch_lower_bound()
    except ValueError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    ply = ply_bound()
    counting_proof = {
        "note": "S >= 3 is conditional on K = 118 and is false in general: "
        "1. Nf3 Nf6 2. Ng1 Ng8 played four times is a legal game ending in "
        "fivefold repetition with K = 1 and S = 0. The theorem is a case "
        "split, recorded below as `ply_bound`.",
        "minimum_switches_at_max_k": switch.minimum_switches,
        "minimum_switches": switch.minimum_switches,
        "max_plies": switch.max_plies,
        "ply_bound": {
            "max_critical_segments": ply.max_critical_segments,
            "below_max_k": ply.below_max_k,
            "at_max_k": ply.at_max_k,
            "max_plies": ply.max_plies,
            "binding_case": ply.binding_case,
            "statement": ply.describe(),
        },
        # `refuted` and `shortfall` are derived properties, so asdict() drops
        # them — and they are the two a reader checks first.
        "refuted": [
            {**dataclasses.asdict(r), "refuted": r.refuted, "shortfall": r.shortfall}
            for r in switch.refuted_shapes
        ],
    }
    print(f"counting    {switch.describe()}")
    print(f"theorem     {ply.describe().splitlines()[-1].strip()}")
    if ply.max_plies != switch.max_plies:
        problems.append(
            f"the case split gives {ply.max_plies}, not {switch.max_plies}"
        )

    # --- the two decisions ------------------------------------------------
    # Each shape is also re-solved with the home-rank lemma switched off. The
    # no-lemma column is what shows the lemma is carrying exactly the shapes
    # its section claims and nothing else is quietly leaning on it — it was
    # reported in the README table but recorded nowhere a re-run could check.
    decisions = []
    refuted_by_counting = {r.colours for r in refutations()}
    for ending in ENDINGS:
        for shape in all_shapes(4):
            solver_result = solve(shape, ending=ending, time_limit=SOLVER_TIME_LIMIT)
            without_lemma = solve(
                shape,
                ending=ending,
                home_rank_limit=False,
                time_limit=SOLVER_TIME_LIMIT,
            )
            independent = analyse_independently(shape, ending=ending)
            agree = solver_result.feasible == independent.feasible
            if not agree:
                problems.append(f"the two methods disagree on {shape} ({ending})")
            counted = shape.colours in refuted_by_counting
            if counted and solver_result.feasible:
                problems.append(
                    f"the solver contradicts the counting proof on "
                    f"{shape} ({ending})"
                )
            if solver_result.feasible and not without_lemma.feasible:
                # Dropping a constraint can only widen the feasible set.
                problems.append(
                    f"removing the lemma made {shape} ({ending}) infeasible, "
                    "which is impossible for a dropped constraint"
                )
            decisions.append(
                {
                    "ending": ending,
                    "shape": str(shape),
                    "switches": shape.switches,
                    "cp_sat": solver_result.status,
                    "cp_sat_feasible": solver_result.feasible,
                    "cp_sat_without_lemma": without_lemma.status,
                    "cp_sat_without_lemma_feasible": without_lemma.feasible,
                    "independent_feasible": independent.feasible,
                    "independent_max_pawn_moves": independent.max_pawn_moves,
                    "independent_max_k": independent.max_k,
                    "independent_account": independent.account,
                    "refuted_by_counting": counted,
                    "agree": agree,
                }
            )

    feasible = [d for d in decisions if d["cp_sat_feasible"]]
    best_switches = min(d["switches"] for d in feasible)
    print(
        f"decisions   {len(decisions)} shape×ending pairs, all agree: "
        f"{all(d['agree'] for d in decisions)}"
    )
    for ending in ENDINGS:
        per = min(
            d["switches"]
            for d in decisions
            if d["cp_sat_feasible"] and d["ending"] == ending
        )
        print(f"            {ending:>9}: minimum feasible S = {per}")
    if best_switches != switch.minimum_switches:
        problems.append(
            f"the solver's minimum S ({best_switches}) does not match the "
            f"counting proof ({switch.minimum_switches})"
        )

    lemma_alone = [
        f"{d['shape']} ({d['ending']})"
        for d in decisions
        if not d["cp_sat_feasible"] and d["cp_sat_without_lemma_feasible"]
    ]
    print(f"lemma alone {', '.join(lemma_alone) or 'none'}")

    # --- the models, so anyone can re-run the UNSAT ------------------------
    # Wiped first: a stale model file from an earlier layout is worse than a
    # missing one, because it looks like part of the current certificate.
    models = out / "models"
    if models.exists():
        shutil.rmtree(models)
    models.mkdir()
    for ending in ENDINGS:
        directory = models / ending
        directory.mkdir(exist_ok=True)
        for shape in all_shapes(4):
            model, _ = build(shape, ending=ending)
            name = str(shape).replace(" ", "")
            (directory / f"{name}.pb.txt").write_text(
                str(model.proto), encoding="utf-8"
            )
            # The lemma-off variant, so the no-lemma column can be re-run too.
            bare, _ = build(shape, ending=ending, home_rank_limit=False)
            (directory / f"{name}.no-lemma.pb.txt").write_text(
                str(bare.proto), encoding="utf-8"
            )
    exported = sorted(models.rglob("*.pb.txt"))
    print(
        f"models      {len(exported)} exported, {len(ENDINGS)} endings × "
        f"{len(all_shapes(4))} shapes × with/without the lemma"
    )

    # --- the soundness check that licenses all of it -----------------------
    accepted = validate(skeleton)
    print(f"soundness   the model accepts the published game: {accepted.accepted}")
    if not accepted.accepted:
        problems.append("the model rejects a game that exists")

    # --- what the reader can hash ------------------------------------------
    artefacts = {
        str(path.relative_to(out)): sha256(path)
        for path in sorted(out.rglob("*"))
        if path.is_file() and path.name not in ("certificate.json", "manifest.json")
    }

    claim = {
        "statement": f"no legal chess game exceeds {ply.max_plies:,} ply",
        "K_bound": bound.total,
        "minimum_switches": switch.minimum_switches,
        "minimum_switches_by_ending": {
            ending: min(
                d["switches"]
                for d in decisions
                if d["cp_sat_feasible"] and d["ending"] == ending
            )
            for ending in ENDINGS
        },
        "max_plies": SEGMENT_TARGET * bound.total - switch.minimum_switches,
        "endings_covered": list(ENDINGS),
        "attained_by": "longest.pgn (in this directory)",
    }

    bound_terms = {
        "note": "K = (P - O) + (C + T). Neither half knows how the game ends, "
        "which is why one bound covers checkmate and every draw alike.",
        "pawn_minus_overlap_bound": MAX_PAWN_MINUS_OVERLAP,
        "captures_plus_closing_bound": MAX_CAPTURES_PLUS_CLOSING,
        "total": bound.total,
        "pawn_minus_overlap": {
            "unresolved_origin_pair_move_cap": 10,
            "resolved_origin_pair_move_cap": 12,
            "pawn_moves_ceiling": "min(96, 80 + 2f)",
            "overlap_floor": "O >= f",
            "maximiser": {
                "resolved_files": envelope.resolved_files,
                "pawn_moves": envelope.pawn_moves,
                "overlaps": envelope.overlaps,
                "value": envelope.value,
            },
        },
        "captures_plus_closing": {
            "capturable_pieces": MAX_CAPTURABLE,
            "bound": captures_plus_closing_bound(),
            "profiles": {
                profile.name: {
                    "captures": profile.captures,
                    "closing": profile.closing_segment,
                    "total": profile.total,
                    "why": profile.why,
                }
                for profile in ending_profiles()
            },
        },
        "equality_conditions": {
            "resolved_files": equality.resolved_files,
            "pawn_moves": equality.pawn_moves,
            "overlaps": equality.overlaps,
            "captures_plus_closing": equality.captures_plus_closing,
            "moves_per_pawn": equality.moves_per_pawn,
            "every_pawn_promotes": equality.every_pawn_promotes,
        },
        # Kept because they are what the attained game actually shows, and a
        # reader comparing the certificate against the PGN needs them.
        "checkmate": {
            "pawn_moves": MAX_PAWN_MOVES,
            "captures": MAX_CAPTURES,
            "overlaps": MINIMUM_OVERLAPS,
            "closing_segment": 1,
            "total": MAX_PAWN_MOVES + MAX_CAPTURES - MINIMUM_OVERLAPS + 1,
        },
        "draw": {
            "pawn_moves": MAX_PAWN_MOVES,
            "captures": MAX_CAPTURES_DRAW,
            "overlaps": MINIMUM_OVERLAPS,
            "closing_segment": 0,
            "total": MAX_PAWN_MOVES + MAX_CAPTURES_DRAW - MINIMUM_OVERLAPS,
        },
    }

    provenance = {
        "source_commit": commit,
        "source_tree_hash": tree,
        "worktree_clean": clean,
        "worktree_dirt": "" if clean else dirt,
        "python": platform.python_version(),
        "ortools": version("ortools"),
        "chess": version("chess"),
        "seed": args.seed,
        "solver": {
            "max_time_in_seconds": SOLVER_TIME_LIMIT,
            "note": "UNKNOWN raises Inconclusive rather than being reported as "
            "infeasible; a timeout is not a refutation.",
        },
        "inputs": inputs,
    }

    # How far the rebuilt game diverges from the published reference: same
    # skeleton, freshly packed filler. The figure is quoted in the paper's
    # witness section, and recording it here pins it byte-for-byte — if the
    # packer's seeding ever changes, check_certificate.py fails rather than
    # letting the quoted number go stale.
    reference = Path("data/longest.pgn")
    from long_chess.verifier import moves_from_pgn

    reference_moves = moves_from_pgn(reference)
    padded_moves = list(padded.moves)
    differing = sum(
        1 for a, b in zip(padded_moves, reference_moves, strict=True) if a != b
    )
    print(
        f"divergence  {differing} of {len(padded_moves)} plies differ "
        "from the reference"
    )

    game = {
        "plies": result.plies,
        "termination": result.termination.value,
        "critical_segments": result.critical_count,
        "slack": stats.slack,
        "sha256": artefacts["longest.pgn"],
        "reference_sha256": sha256(reference),
        "plies_differing_from_reference": differing,
    }

    caveats = [
        "This is our own formalisation and has not been reviewed by anyone else.",
        "The bound is a counting proof (long_chess.bound): P - O <= 88, "
        "C + T <= 30, K <= 118, and every S <= 2 block shape refuted by hand. "
        "CP-SAT and long_chess.model.independent re-decide the same question "
        "and agree, but neither is the proof.",
        "long_chess.model.independent is an independent *arithmetic* "
        "cross-check, not a second proof: it declares its own constants but "
        "reads the same Shape and works in the same numbers.",
        "The model is a relaxation: it knows nothing about squares, "
        "reachability, or whether the quiet bridges between events exist. "
        "That is what makes INFEASIBLE mean 'no legal game'.",
        "CP-SAT emits no machine-checkable UNSAT proof. Re-running the exported "
        "models is what a third party has instead.",
        "An earlier version capped an unresolved origin pair at 4 combined pawn "
        "moves. That was false -- once one of the two pawns is captured by some "
        "other piece the survivor runs on -- and false in the direction that "
        "turns legal games into UNSAT. The correct cap is 10, exhaustively "
        "re-derived, and the conclusion is unchanged: P - O <= 88 still, and "
        "K <= 118 still.",
        "Both endings are checked. A draw may take all 30 pieces rather "
        "than 29, but the thirtieth leaves king against king, which is dead "
        "and ends the game where it stands -- giving up the closing segment. "
        "The trade is exactly even and the bound does not move.",
        "is_insufficient_material is not a decision procedure for FIDE dead "
        "positions, so this verifier ends games later than FIDE would. That "
        "is safe for the upper bound -- omitting the constraint loosens the "
        "model -- and safe for the attained game too, because a game ending "
        "in checkmate contains no dead position: from any position in it, "
        "the rest of the game is a series of legal moves reaching mate.",
    ]

    # The manifest is everything that must come out identical on a re-run. It
    # holds no timestamp and no provenance — a re-run happens at a different
    # commit, on a different machine, and if that changed the manifest then
    # nobody could ever check it. Provenance lives in certificate.json, which
    # answers a different question: not "are the numbers the same" but "what
    # produced them".
    manifest = {
        "claim": claim,
        "bound_terms": bound_terms,
        "counting_proof": counting_proof,
        "decisions": decisions,
        "ruled_out_by_lemma_alone": lemma_alone,
        "game": game,
        "artefacts": artefacts,
        "artefacts_not_committed": list(NOT_COMMITTED),
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    certificate = {
        "produced": produced_at(),
        "provenance": provenance,
        # Retained at the top level: the previous layout had them here, and a
        # reader following an older description should not silently find
        # nothing.
        "commit": commit,
        "python": provenance["python"],
        "ortools": provenance["ortools"],
        "claim": claim,
        "bound_terms": bound_terms,
        "counting_proof": counting_proof,
        "lemmas": lemmas,
        "decisions": decisions,
        "ruled_out_by_lemma_alone": lemma_alone,
        "game": game,
        "artefacts": artefacts,
        "artefacts_not_committed": list(NOT_COMMITTED),
        "manifest_sha256": sha256(out / "manifest.json"),
        "caveats": caveats,
    }
    (out / "certificate.json").write_text(
        json.dumps(certificate, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nwrote {out}/")
    for path in sorted(out.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(out)}  ({path.stat().st_size:,} bytes)")

    if problems:
        print("\nFAIL:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(
        f"\nclaim: no legal game exceeds {switch.max_plies:,} ply, "
        "and this one attains it"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
