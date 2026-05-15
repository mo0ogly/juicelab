"""Schema migration smoke tests for Phase 1."""
# Note: this test uses module-level reload (importlib.reload(db)) which is
# NOT safe under pytest-xdist parallel workers. The project runs tests
# serially; if -n is ever added, refactor to a fixture-scope='session'
# pattern or a process-local sqlite path that does not require reload.
from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    import importlib, sys
    if "db" in sys.modules: del sys.modules["db"]
    import db
    importlib.reload(db)
    db.init_schema()
    return tmp_path / "d.sqlite"


def _cols(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as c:
        return {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}


def test_student_tag_table_exists(fresh_db):
    cols = _cols(fresh_db, "student_tag")
    assert {"student_token", "cohort_id", "status", "updated_at"} <= cols


def test_student_note_table_exists(fresh_db):
    cols = _cols(fresh_db, "student_note")
    assert {"student_token", "cohort_id", "body", "updated_at"} <= cols


def test_alerts_table_exists(fresh_db):
    cols = _cols(fresh_db, "alerts")
    assert {"id", "cohort_id", "student_token", "kind", "challenge_key", "created_at", "ack_at"} <= cols
