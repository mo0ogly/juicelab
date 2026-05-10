"""verify_proof.py - Verify a JuiceLab tamper-evident lab proof.

A signed proof has the structure :

    # JuiceLab proof - <name>
    ... markdown body ...

    ---
    PROOF: HMAC-SHA256
    SCHEME: v1
    TIMESTAMP: 2026-05-09T15:30:42+00:00
    STUDENT: <token>
    CHALLENGE: <key>
    SIGNATURE: <hex>

The signature covers everything from the start of the file up to (but not
including) the line "SIGNATURE: <hex>".

Usage :
    python verify_proof.py <path-to.md> [--secret SECRET | --secret-env VAR]

Exit codes :
    0  signature valid
    1  signature invalid or signature line missing
    2  IO/parse error or missing secret
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sys
from pathlib import Path


SIGNATURE_LINE_PREFIX = "SIGNATURE: "


def verify(content: str, secret: bytes) -> tuple[bool, dict[str, str]]:
    """Return (ok, metadata). ok is True iff the signature checks out."""
    idx = content.rfind("\n" + SIGNATURE_LINE_PREFIX)
    if idx < 0:
        if content.startswith(SIGNATURE_LINE_PREFIX):
            idx = 0
        else:
            return False, {"error": "no SIGNATURE line found"}

    signed_payload = content[: idx + 1] if idx > 0 else ""
    sig_block = content[idx + 1 :] if idx > 0 else content
    sig_line = sig_block.splitlines()[0] if sig_block else ""
    if not sig_line.startswith(SIGNATURE_LINE_PREFIX):
        return False, {"error": "malformed SIGNATURE line"}
    expected_sig = sig_line[len(SIGNATURE_LINE_PREFIX) :].strip()
    actual = hmac.new(secret, signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    meta: dict[str, str] = {}
    for line in signed_payload.splitlines():
        for key in ("PROOF", "SCHEME", "TIMESTAMP", "STUDENT", "CHALLENGE"):
            prefix = key + ": "
            if line.startswith(prefix):
                meta[key.lower()] = line[len(prefix) :].strip()

    return hmac.compare_digest(actual, expected_sig), meta


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="path to the .md proof file")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--secret", help="HMAC secret (>=16 chars); not recommended on the CLI")
    grp.add_argument("--secret-env", default="DASHBOARD_PROOF_SECRET", help="env var holding the HMAC secret (default: DASHBOARD_PROOF_SECRET)")
    args = parser.parse_args(argv)

    secret_raw = args.secret or os.environ.get(args.secret_env, "")
    if len(secret_raw) < 16:
        sys.stderr.write("ERROR: HMAC secret missing or shorter than 16 chars (use --secret or set " + args.secret_env + ")\n")
        return 2
    secret = secret_raw.encode("utf-8")

    try:
        content = Path(args.path).read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write("ERROR: cannot read " + args.path + " : " + str(exc) + "\n")
        return 2

    ok, meta = verify(content, secret)
    label = "VALID  " if ok else "INVALID"
    print(label + " | " + args.path)
    for k in ("scheme", "timestamp", "student", "challenge"):
        if k in meta:
            print("  " + k + ": " + meta[k])
    if "error" in meta:
        print("  reason: " + meta["error"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
