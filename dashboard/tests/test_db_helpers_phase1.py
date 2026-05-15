"""DB helpers for tags, notes, alerts (Phase 1)."""
# Note: this test uses module-level reload (importlib.reload(db)) which is
# NOT safe under pytest-xdist parallel workers. The project runs tests
# serially; if -n is ever added, refactor to a fixture-scope='session'
# pattern or a process-local sqlite path that does not require reload.
from __future__ import annotations
import pytest, sys, importlib
from datetime import datetime, timezone


@pytest.fixture
def db_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    if "db" in sys.modules: del sys.modules["db"]
    import db
    importlib.reload(db)
    db.init_schema()
    return db


def test_set_and_get_tag(db_module):
    now = datetime.now(timezone.utc).isoformat()
    with db_module.get_connection() as c:
        db_module.set_tag(c, "tok123", "M2-IA-2026", "a_voir", now)
        c.commit()
        result = db_module.get_tag(c, "tok123", "M2-IA-2026")
    assert result == "a_voir"


def test_get_tag_default_none(db_module):
    with db_module.get_connection() as c:
        result = db_module.get_tag(c, "missing", "M2-IA-2026")
    assert result is None


def test_set_and_get_note(db_module):
    now = datetime.now(timezone.utc).isoformat()
    with db_module.get_connection() as c:
        db_module.set_note(c, "tok123", "M2-IA-2026", "rusee sur XSS", now)
        c.commit()
        result = db_module.get_note(c, "tok123", "M2-IA-2026")
    assert result == "rusee sur XSS"


def test_insert_and_recent_alerts(db_module):
    now = datetime.now(timezone.utc).isoformat()
    with db_module.get_connection() as c:
        db_module.insert_alert(c, "M2-IA-2026", "tok123", "blocked", "xss-stored", now)
        db_module.insert_alert(c, "M2-IA-2026", "tok456", "stuck", "sql-inject", now)
        c.commit()
        rows = db_module.recent_alerts(c, "M2-IA-2026", limit=10)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"blocked", "stuck"}
