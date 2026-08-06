#!/usr/bin/env python3
"""Download the reference 17,697-ply game to data/longest.pgn.

The file is not in Tom 7's repository -- longest.cc writes it at runtime -- so
the published copy at tom7.org is the artefact. Two wrinkles worth knowing:

- tom7.org's TLS fails modern OpenSSL with "unsafe legacy renegotiation
  disabled", so we fall back to plain HTTP.
- Plain HTTP means no integrity guarantee, hence the hash check. Even so,
  nothing downstream trusts this file: the verifier re-derives legality from
  scratch and the tests pin the ply count.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "http://tom7.org/chess/longest.pgn"
EXPECTED_SHA256 = "6700b7b70260c9b4448d58c610601cab938dd0e01392bd876d3379630de680bb"
DESTINATION = Path(__file__).parent.parent / "data" / "longest.pgn"


def main() -> int:
    if DESTINATION.exists():
        digest = hashlib.sha256(DESTINATION.read_bytes()).hexdigest()
        if digest == EXPECTED_SHA256:
            print(f"{DESTINATION} already present and matches")
            return 0
        print(f"{DESTINATION} exists but hashes {digest}; re-downloading")

    print(f"fetching {URL}")
    with urllib.request.urlopen(URL, timeout=120) as response:
        data = response.read()

    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        print(f"hash mismatch: got {digest}, expected {EXPECTED_SHA256}")
        return 1

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_bytes(data)
    print(f"wrote {DESTINATION} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
