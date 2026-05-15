"""Phase 3 Task 5 : cohort PDF route (tolerant of 503 if weasyprint missing)."""
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
    for m in ["app", "db", "pdf_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    a = create_app()
    c = a.test_client()
    c.post("/api/cohorts", json={"cohort_id": "demo"}, headers=AUTH)
    return c


def test_pdf_route_returns_pdf_or_503(client):
    r = client.get("/admin/cohort/report.pdf?cohort=demo", headers=AUTH)
    assert r.status_code in (200, 503), f"Unexpected status {r.status_code}"
    if r.status_code == 200:
        assert r.mimetype == "application/pdf"
        assert r.data[:4] == b"%PDF"
    else:
        # 503 fallback : weasyprint not installed
        assert b"weasyprint" in r.data.lower()
