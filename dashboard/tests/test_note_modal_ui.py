"""Phase 2 Task 7 : note modal markup smoke."""
from __future__ import annotations
import sys, pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

AUTH = {"X-Teacher-Token": "teacher-test-token-very-long-32chars!!"}


@pytest.fixture
def client(tmp_path, monkeypatch):
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


def test_note_modal_markup_present(client):
    r = client.get("/dashboard?cohort=demo", headers=AUTH)
    assert r.status_code == 200
    body = r.data.decode()
    assert 'id="note-modal-backdrop"' in body
    assert 'id="note-textarea"' in body
    assert 'id="note-save-btn"' in body
