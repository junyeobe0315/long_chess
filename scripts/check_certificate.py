#!/usr/bin/env python3
"""Re-run the certificate and check the stored one still describes the code.

    uv run --extra solver python scripts/check_certificate.py \
        data/skeleton.json data/certificate

Regenerates the whole certificate into a temporary directory and compares its
``manifest.json`` — the run-invariant half — against the one committed. A
mismatch means the artefacts in the repository no longer match what the code
produces, which is the only way a stale certificate announces itself.

The manifest deliberately carries no timestamp and no provenance, so this
comparison is byte for byte and works from any commit, on any machine.
``certificate.json`` is where the timestamp and the commit live, and it is not
compared here.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check_certificate")
    parser.add_argument("skeleton", type=Path)
    parser.add_argument("certificate", type=Path)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="passed through to certify.py",
    )
    return parser


def differences(stored: object, fresh: object, path: str = "") -> list[str]:
    """Where two decoded manifests disagree, as dotted paths."""
    if type(stored) is not type(fresh):
        return [f"{path or '.'}: {type(stored).__name__} vs {type(fresh).__name__}"]
    if isinstance(stored, dict):
        found = []
        for key in sorted(set(stored) | set(fresh)):
            where = f"{path}.{key}" if path else str(key)
            if key not in stored:
                found.append(f"{where}: only in the fresh run")
            elif key not in fresh:
                found.append(f"{where}: only in the stored certificate")
            else:
                found += differences(stored[key], fresh[key], where)
        return found
    if isinstance(stored, list):
        if len(stored) != len(fresh):
            return [f"{path}: {len(stored)} entries stored, {len(fresh)} fresh"]
        return [
            difference
            for index, (a, b) in enumerate(zip(stored, fresh, strict=True))
            for difference in differences(a, b, f"{path}[{index}]")
        ]
    return [] if stored == fresh else [f"{path}: {stored!r} stored, {fresh!r} fresh"]


def audit_stored_artefacts(root: Path, manifest: dict) -> list[str]:
    """Hash the committed artefacts against what the manifest records.

    The byte-for-byte manifest comparison proves the *code* still produces
    these numbers; it never reads the committed artefact files. A corrupted
    or tampered file sitting beside an intact manifest would pass it, so the
    stored files are hashed here directly. Artefacts the certificate declares
    gitignored-and-regenerable are exempt when absent.
    """
    import hashlib

    problems = []
    exempt = set(manifest.get("artefacts_not_committed", []))
    for name, expected in sorted(manifest.get("artefacts", {}).items()):
        path = root / name
        if not path.is_file():
            if Path(name).name not in exempt:
                problems.append(f"{name}: missing and not declared regenerable")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            problems.append(
                f"{name}: sha256 {actual[:12]}... does not match the "
                f"recorded {expected[:12]}..."
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stored_path = args.certificate / "manifest.json"
    if not stored_path.exists():
        print(
            f"FAIL: {stored_path} is missing; run scripts/certify.py",
            file=sys.stderr,
        )
        return 1

    # The cheap, self-contained half first: the committed files themselves,
    # against the hashes the stored manifest records for them. This needs no
    # re-run and no clean worktree.
    stored_bytes = stored_path.read_bytes()
    stored_manifest = json.loads(stored_bytes.decode("utf-8"))
    audited = audit_stored_artefacts(args.certificate, stored_manifest)
    if audited:
        print(
            "FAIL: stored artefacts do not match the manifest's hashes",
            file=sys.stderr,
        )
        for problem in audited:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(
        "stored artefacts hashed against the manifest: "
        f"{len(stored_manifest.get('artefacts', {}))} recorded"
    )

    with tempfile.TemporaryDirectory() as scratch:
        command = [
            sys.executable,
            str(Path(__file__).with_name("certify.py")),
            str(args.skeleton),
            "-o",
            scratch,
        ]
        if args.allow_dirty:
            command.append("--allow-dirty")
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            print(completed.stdout)
            print(completed.stderr, file=sys.stderr)
            print("FAIL: regenerating the certificate failed", file=sys.stderr)
            return completed.returncode
        fresh_bytes = (Path(scratch) / "manifest.json").read_bytes()

    if stored_bytes == fresh_bytes:
        print(f"manifest matches byte for byte ({len(stored_bytes):,} bytes)")
        return 0

    found = differences(
        json.loads(stored_bytes.decode("utf-8")),
        json.loads(fresh_bytes.decode("utf-8")),
    )
    print("FAIL: the stored certificate does not match a fresh run", file=sys.stderr)
    for difference in found[:40] or ["(identical once decoded — formatting differs)"]:
        print(f"  {difference}", file=sys.stderr)
    if len(found) > 40:
        print(f"  ... and {len(found) - 40} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
