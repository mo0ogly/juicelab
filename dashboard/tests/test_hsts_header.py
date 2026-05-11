"""Coverage : HSTS opt-in via DASHBOARD_HTTPS environment variable.

HSTS must NOT be set by default (plain-HTTP local dev). It must appear
only when DASHBOARD_HTTPS=true is explicitly set. Misconfiguration
(false / unset) must produce no Strict-Transport-Security header.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKEN = "teacher-test-token-very-long-32chars!!"


def _make_client(tmp_path, monkeypatch, https_value=None):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    if https_value is None:
        monkeypatch.delenv("DASHBOARD_HTTPS", raising=False)
    else:
        monkeypatch.setenv("DASHBOARD_HTTPS", https_value)
    for mod in ("app", "db"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    return app_mod.create_app().test_client()


def test_hsts_absent_when_https_unset(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch, https_value=None)
    r = c.get("/api/health")
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_absent_when_https_false(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch, https_value="false")
    r = c.get("/api/health")
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_present_when_https_true(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch, https_value="true")
    r = c.get("/api/health")
    hsts = r.headers.get("Strict-Transport-Security", "")
    assert hsts != ""
    assert "max-age=" in hsts
    # Preload requirement : max-age >= 1 year (31536000s) for HSTS preload
    # list submission. Current value is 2 years (63072000).
    import re
    m = re.search(r"max-age=(\d+)", hsts)
    assert m is not None
    assert int(m.group(1)) >= 31536000
    assert "includeSubDomains" in hsts
    assert "preload" in hsts


def test_hsts_case_insensitive_true(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch, https_value="TRUE")
    r = c.get("/api/health")
    assert "Strict-Transport-Security" in r.headers


def test_hsts_invalid_value_treated_as_false(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch, https_value="yes")
    r = c.get("/api/health")
    # "yes" is not "true", so HSTS must NOT be set.
    assert "Strict-Transport-Security" not in r.headers
