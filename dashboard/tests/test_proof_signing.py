"""Coverage : sign_proof + build_proof_markdown + verify_proof.verify.

Pure-Python unit tests, no Flask context required. Validates the HMAC
round-trip : a body signed by sign_proof must verify under the same
secret, and tampering with any byte must invalidate it.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proof_routes import build_proof_markdown, sign_proof
from verify_proof import verify

SECRET = b"x" * 32


def _ev(t, data, ts="2026-05-11T08:00:00Z"):
    return {"event_type": t, "data": data, "client_ts": ts, "server_ts": ts, "level_id": 1}


def _sample_events() -> list[dict]:
    return [
        _ev("session_start", {}, "2026-05-11T08:00:00Z"),
        _ev("hint_revealed", {"hint_id": "h1", "level": 1, "cost_pct": 10},
            "2026-05-11T08:05:00Z"),
        _ev("journal_filled",
            {"phase": "after", "text": "I solved it by tampering with the JWT."},
            "2026-05-11T08:30:00Z"),
        _ev("quiz_submitted", {"score_pct": 100, "answers": {"q1": "A"}},
            "2026-05-11T08:32:00Z"),
        _ev("challenge_solved", {"flag": "fake"}, "2026-05-11T08:35:00Z"),
    ]


def _build_signed(events=None) -> str:
    body = build_proof_markdown(
        student_token="student-token-1234567890abcdef",
        student_name="Test Student",
        cohort_id="M2-IA-2026",
        challenge_key="weakPasswordChallenge",
        challenge_name="Login Admin",
        challenge_category="Broken Authentication",
        challenge_difficulty=1,
        challenge_description="Login as the administrator using the weak default password.",
        events=events if events is not None else _sample_events(),
    )
    return sign_proof(body, secret=SECRET, student_token="student-token-1234567890abcdef",
                      challenge_key="weakPasswordChallenge")


def test_sign_proof_roundtrip_valid():
    full = _build_signed()
    ok, meta = verify(full, SECRET)
    assert ok is True
    assert meta["scheme"] == "v1"
    assert meta["challenge"] == "weakPasswordChallenge"
    assert meta["student"] == "student-token-1234567890abcdef"


def test_sign_proof_tampered_body_fails():
    full = _build_signed()
    tampered = full.replace("Login Admin", "Login Hacker")
    ok, _ = verify(tampered, SECRET)
    assert ok is False


def test_sign_proof_tampered_signature_fails():
    full = _build_signed()
    last_nl = full.rfind("SIGNATURE: ")
    tampered = full[:last_nl] + "SIGNATURE: " + "0" * 64 + "\n"
    ok, _ = verify(tampered, SECRET)
    assert ok is False


def test_sign_proof_wrong_secret_fails():
    full = _build_signed()
    ok, _ = verify(full, b"y" * 32)
    assert ok is False


def test_sign_proof_no_signature_line():
    body = build_proof_markdown(
        student_token="s1", student_name="S", cohort_id="C", challenge_key="k",
        challenge_name="N", challenge_category="Cat", challenge_difficulty=1,
        challenge_description="d", events=[],
    )
    ok, meta = verify(body, SECRET)
    assert ok is False
    assert "no SIGNATURE" in meta["error"]


def test_sign_proof_empty_secret_raises():
    with pytest.raises(RuntimeError, match="DASHBOARD_PROOF_SECRET"):
        sign_proof("body", secret=b"", student_token="s", challenge_key="k")


def test_build_proof_markdown_includes_metadata():
    body = build_proof_markdown(
        student_token="abc", student_name="Alice", cohort_id="M2-IA-2026",
        challenge_key="xssTier1Challenge", challenge_name="Reflected XSS",
        challenge_category="XSS", challenge_difficulty=1,
        challenge_description="Trigger a reflected XSS on the search bar.",
        events=_sample_events(),
    )
    assert "Alice" in body
    assert "M2-IA-2026" in body
    assert "xssTier1Challenge" in body
    assert "Reflected XSS" in body


def test_build_proof_markdown_journal_text_included():
    body = build_proof_markdown(
        student_token="abc", student_name="Bob", cohort_id="C", challenge_key="k",
        challenge_name="N", challenge_category="Cat", challenge_difficulty=2,
        challenge_description="d", events=_sample_events(),
    )
    assert "tampering with the JWT" in body


def test_build_proof_markdown_quiz_score_included():
    body = build_proof_markdown(
        student_token="abc", student_name="Bob", cohort_id="C", challenge_key="k",
        challenge_name="N", challenge_category="Cat", challenge_difficulty=2,
        challenge_description="d", events=_sample_events(),
    )
    assert "100" in body


def test_build_proof_markdown_hint_recorded():
    body = build_proof_markdown(
        student_token="abc", student_name="Bob", cohort_id="C", challenge_key="k",
        challenge_name="N", challenge_category="Cat", challenge_difficulty=2,
        challenge_description="d", events=_sample_events(),
    )
    # hint_revealed event must move "Indices consommes" out of "_aucun_" state
    assert "aucun" not in body.lower().split("indices consommes")[1].split("##")[0]


def test_verify_handles_signature_line_at_start():
    bad = "SIGNATURE: deadbeef\n"
    ok, meta = verify(bad, SECRET)
    assert ok is False


def test_verify_malformed_signature_line():
    content = "body content\n---\nPROOF: HMAC-SHA256\nNOTSIG: x\n"
    ok, meta = verify(content, SECRET)
    assert ok is False
    assert "error" in meta
