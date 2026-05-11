"""Coverage : verify_proof.main CLI path.

verify() is already covered by test_proof_signing.py. This file exercises
the CLI wrapper (argparse, env secret loading, IO error path, valid
output format).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify_proof import main

SECRET = "verify-cli-test-secret-1234567890abc"


def _make_signed_proof(tmp_path: Path, secret: str = SECRET) -> Path:
    body = "# Proof body\n\nlab content here\n\n---\nPROOF: HMAC-SHA256\nSCHEME: v1\nTIMESTAMP: 2026-05-11T10:00:00+00:00\nSTUDENT: stud\nCHALLENGE: chal\n"
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    path = tmp_path / "p.md"
    path.write_text(body + "SIGNATURE: " + sig + "\n", encoding="utf-8")
    return path


def test_cli_valid_signature(tmp_path, monkeypatch, capsys):
    proof = _make_signed_proof(tmp_path)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", SECRET)
    rc = main([str(proof)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "VALID" in out
    assert "scheme: v1" in out
    assert "student: stud" in out
    assert "challenge: chal" in out


def test_cli_invalid_signature(tmp_path, monkeypatch, capsys):
    proof = _make_signed_proof(tmp_path)
    text = proof.read_text(encoding="utf-8")
    proof.write_text(text.replace("lab content", "tampered"), encoding="utf-8")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", SECRET)
    rc = main([str(proof)])
    assert rc == 1
    assert "INVALID" in capsys.readouterr().out


def test_cli_wrong_secret(tmp_path, monkeypatch, capsys):
    proof = _make_signed_proof(tmp_path)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "wrong-secret-1234567890abcdef")
    rc = main([str(proof)])
    assert rc == 1
    assert "INVALID" in capsys.readouterr().out


def test_cli_secret_via_flag(tmp_path, capsys):
    proof = _make_signed_proof(tmp_path)
    rc = main([str(proof), "--secret", SECRET])
    assert rc == 0
    assert "VALID" in capsys.readouterr().out


def test_cli_secret_missing(tmp_path, monkeypatch, capsys):
    proof = _make_signed_proof(tmp_path)
    monkeypatch.delenv("DASHBOARD_PROOF_SECRET", raising=False)
    rc = main([str(proof)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "HMAC secret" in err


def test_cli_secret_too_short(tmp_path, capsys):
    proof = _make_signed_proof(tmp_path)
    rc = main([str(proof), "--secret", "short"])
    assert rc == 2
    assert "shorter than 16" in capsys.readouterr().err


def test_cli_secret_env_var_custom(tmp_path, monkeypatch, capsys):
    proof = _make_signed_proof(tmp_path)
    monkeypatch.setenv("MY_CUSTOM_PROOF_KEY", SECRET)
    rc = main([str(proof), "--secret-env", "MY_CUSTOM_PROOF_KEY"])
    assert rc == 0
    assert "VALID" in capsys.readouterr().out


def test_cli_file_not_found(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", SECRET)
    rc = main([str(tmp_path / "does-not-exist.md")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "cannot read" in err


def test_cli_no_signature_line(tmp_path, monkeypatch, capsys):
    proof = tmp_path / "no-sig.md"
    proof.write_text("just some markdown\n\nno signature footer\n", encoding="utf-8")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", SECRET)
    rc = main([str(proof)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INVALID" in out
    assert "no SIGNATURE" in out
