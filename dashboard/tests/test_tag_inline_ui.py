"""Phase 2 Task 6 : inline tag select in matrix + summary includes tags."""
from __future__ import annotations
import sys, pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

AUTH = {"X-Teacher-Token": "teacher-test-token-very-long-32chars!!"}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_MONITOR_ENABLED", "0")
    for m in ["app", "db"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    a = create_app()
    c = a.test_client()
    c.post("/api/cohorts", json={"cohort_id": "demo"}, headers=AUTH)
    return c


def test_dashboard_has_tag_select(app):
    # Seed a student + approve + emit one event so summary.students has at
    # least one row (sorted_students is populated from events filtered by
    # the roster, and the sync gate rejects events from pending students).
    app.post(
        "/api/students",
        json={"cohort_id": "demo", "student_token": "stud-tag-row-1", "display_name": "Alice"},
        headers=AUTH,
    )
    app.post(
        "/api/students/stud-tag-row-1/approve",
        json={"cohort_id": "demo"},
        headers=AUTH,
    )
    app.post(
        "/api/sync",
        json={
            "student_token": "stud-tag-row-1",
            "cohort_id": "demo",
            "event_type": "session_start",
            "client_timestamp": "2026-05-15T10:00:00Z",
        },
    )
    r = app.get("/dashboard?cohort=demo", headers=AUTH)
    assert r.status_code == 200
    body = r.data.decode()
    # Server-rendered <select class="tag-select"> must exist for every row.
    assert 'class="tag-select"' in body
    # The five option values must be present so the prof can pick any tag.
    for value in ("a_voir", "ok", "absent", "a_interroger", "none"):
        assert 'value="' + value + '"' in body
    # The translated label "(aucun)" (FR default) is rendered as the
    # selected option text, not the raw i18n key. The key DOES appear once
    # inside the `window.I18N` catalog dump (same pattern as every other
    # key), so we cannot use a naive `'TAG_NONE' not in body` here.
    assert '(aucun)' in body or '(none)' in body


def test_cohort_summary_includes_tags(app):
    r = app.get("/api/cohort?cohort=demo", headers=AUTH)
    assert r.status_code == 200
    j = r.get_json()
    assert "tags" in j
    assert isinstance(j["tags"], dict)
