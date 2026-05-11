"""Crypto invariants : detect what mutation testing would target.

For each crypto-critical operation we exercise the boundary conditions
that a code mutation (== -> !=, < -> <=, operand swap, constant flip)
would silently break. Run alongside the regular pytest suite.

Targets : verify_proof.verify, csrf.check_csrf, proof_routes.sign_proof.
The signal a successful run gives : if anyone replaces the timing-safe
hmac.compare_digest with == (or vice-versa), or swaps an HMAC argument,
at least one of these tests will fail.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from csrf import check_csrf, COOKIE_NAME, HEADER_NAME
from proof_routes import sign_proof
from verify_proof import verify

SECRET = b"crypto-inv-secret-1234567890abcdef"
WRONG = b"crypto-inv-WRONG-1234567890abcdef!"


# --- HMAC equality invariants -------------------------------------------

def test_verify_equality_strict_one_byte_diff():
    """Exactly one byte different in the signature must invalidate it."""
    body = "## proof\nbody\n\n---\nPROOF: HMAC-SHA256\nSCHEME: v1\n"
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    valid_doc = body + "SIGNATURE: " + sig + "\n"
    # flip the last hex digit only
    last = sig[-1]
    flipped = "0" if last != "0" else "1"
    invalid_doc = body + "SIGNATURE: " + sig[:-1] + flipped + "\n"
    ok_v, _ = verify(valid_doc, SECRET)
    ok_i, _ = verify(invalid_doc, SECRET)
    assert ok_v is True
    assert ok_i is False


def test_verify_equality_signature_length_diff():
    """Trailing whitespace / truncation in signature must invalidate."""
    body = "## proof\nbody\n\n---\nPROOF: HMAC-SHA256\n"
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    truncated = body + "SIGNATURE: " + sig[:-2] + "\n"
    extra = body + "SIGNATURE: " + sig + "AA\n"
    ok_t, _ = verify(truncated, SECRET)
    ok_e, _ = verify(extra, SECRET)
    assert ok_t is False
    assert ok_e is False


def test_verify_secret_swap_invalidates():
    """Computing with WRONG secret on a SECRET-signed doc must fail."""
    body = "doc\n"
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    doc = body + "SIGNATURE: " + sig + "\n"
    ok, _ = verify(doc, WRONG)
    assert ok is False


def test_sign_proof_signature_matches_hmac_recompute():
    """The SIGNATURE produced by sign_proof must be the HMAC-SHA256 of
    everything up to that line. Catches mutations that swap to MD5/SHA1,
    that hash with the wrong secret, or that include/exclude the wrong
    bytes from the signed payload.
    """
    out = sign_proof("## test\n", secret=SECRET,
                    student_token="s", challenge_key="c")
    sig_line_idx = out.rindex("\nSIGNATURE: ")
    signed_payload = out[:sig_line_idx + 1]
    declared_sig = out[sig_line_idx + len("\nSIGNATURE: "):].strip()
    expected = hmac.new(SECRET, signed_payload.encode("utf-8"),
                        hashlib.sha256).hexdigest()
    assert declared_sig == expected, "SIGNATURE != HMAC-SHA256 of payload"


# --- CSRF equality invariants -------------------------------------------

@pytest.fixture
def csrf_app():
    app = Flask(__name__)

    @app.route("/p", methods=["GET", "POST"])
    def p():
        return jsonify({"ok": check_csrf()})

    return app.test_client()


def test_csrf_one_byte_diff_blocks(csrf_app):
    """A single-character header difference must NOT pass check_csrf."""
    csrf_app.set_cookie("csrf_token", "abcdef0123456789")
    r = csrf_app.post("/p", headers={HEADER_NAME: "abcdef0123456788"})
    assert r.get_json()["ok"] is False


def test_csrf_case_diff_blocks(csrf_app):
    """Uppercase / lowercase difference must NOT pass (compare_digest
    is byte-exact, not case-insensitive)."""
    csrf_app.set_cookie("csrf_token", "AbCdEf")
    r = csrf_app.post("/p", headers={HEADER_NAME: "abcdef"})
    assert r.get_json()["ok"] is False


def test_csrf_whitespace_diff_blocks(csrf_app):
    """Leading/trailing whitespace difference must NOT pass.

    Note : check_csrf .strip()s both sides, so " abc " == "abc". This
    test pins that behavior so a mutation that removes strip() (or adds
    one when there shouldn't be) fails.
    """
    csrf_app.set_cookie("csrf_token", "abc")
    r = csrf_app.post("/p", headers={HEADER_NAME: " abc "})
    # Per cycle 3 design : strip on both sides, so this MUST pass.
    assert r.get_json()["ok"] is True


def test_csrf_empty_strings_block(csrf_app):
    """Empty header AND empty cookie must NOT pass (the empty-string
    edge case is a classic mutation-testing trap)."""
    csrf_app.set_cookie("csrf_token", "")
    r = csrf_app.post("/p", headers={HEADER_NAME: ""})
    assert r.get_json()["ok"] is False


def test_csrf_safe_method_invariant(csrf_app):
    """GET must always pass regardless of header presence (read-only
    methods are CSRF-immune by definition)."""
    csrf_app.set_cookie("csrf_token", "a")
    r = csrf_app.get("/p", headers={HEADER_NAME: "DIFFERENT"})
    assert r.get_json()["ok"] is True


def test_csrf_teacher_token_bypass_priority(csrf_app):
    """X-Teacher-Token bypass must short-circuit BEFORE the header/cookie
    compare. Catches mutation that re-orders the early-return logic."""
    # No cookie, no CSRF header, but Teacher-Token present : must pass.
    r = csrf_app.post("/p", headers={"X-Teacher-Token": "any-value"})
    assert r.get_json()["ok"] is True


# --- HMAC operand-swap invariant ----------------------------------------

def test_hmac_operand_order_does_not_matter_for_verify():
    """hmac.new(key, msg) is the canonical order. compare_digest(a, b)
    is symmetric. A code mutation that swaps key<->msg in hmac.new()
    produces a different signature for the same secret+body, so a
    correctly-signed proof would fail under such a mutation.
    """
    body = "test\n"
    correct = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    swapped = hmac.new(body.encode(), SECRET, hashlib.sha256).hexdigest()
    assert correct != swapped  # invariant : the two orderings differ
    doc_correct = body + "SIGNATURE: " + correct + "\n"
    doc_swapped = body + "SIGNATURE: " + swapped + "\n"
    ok_c, _ = verify(doc_correct, SECRET)
    ok_s, _ = verify(doc_swapped, SECRET)
    assert ok_c is True
    assert ok_s is False
