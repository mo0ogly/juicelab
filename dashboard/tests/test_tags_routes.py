"""HTTP CRUD for student_tag + student_note (Phase 1, Task 6).

Note: this test uses module-level reload (del sys.modules) which is
NOT safe under pytest-xdist parallel workers. The project runs tests
serially; if -n is ever added, refactor to a fixture-scope='session'
pattern.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_SSE_HEARTBEAT_SEC", "0.5")
    for m in ("app", "db", "tags_routes"):
        if m in sys.modules:
            del sys.modules[m]
    from app import create_app
    flask_app = create_app()
    flask_app.testing = True
    return flask_app


def test_set_tag_requires_auth(app):
    c = app.test_client()
    r = c.post(
        "/api/tag",
        json={"student_token": "x", "cohort_id": "c", "status": "a_voir"},
    )
    assert r.status_code in (401, 403)


def test_set_then_get_tag(app):
    c = app.test_client()
    r1 = c.post(
        "/api/tag",
        json={"student_token": "tok", "cohort_id": "M2-IA-2026", "status": "a_voir"},
        headers=AUTH,
    )
    assert r1.status_code == 200
    r2 = c.get(
        "/api/tag?student_token=tok&cohort=M2-IA-2026",
        headers=AUTH,
    )
    assert r2.status_code == 200
    assert r2.json["status"] == "a_voir"
