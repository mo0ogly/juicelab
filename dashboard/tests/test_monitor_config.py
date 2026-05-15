"""Phase 2 Task 8 : dashboard-config.json overrides monitor seuils."""
from __future__ import annotations
import sys, json, pytest, importlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def db_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    for m in ["db", "monitor"]:
        if m in sys.modules: del sys.modules[m]
    import db
    importlib.reload(db)
    db.init_schema()
    return db


def _insert_event(db_mod, cohort, token, event_type, key, minutes_ago=0):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO events (cohort_id, student_token, event_type, challenge_key, client_ts, server_ts, data_json, instance_label) "
            "VALUES (?, ?, ?, ?, ?, ?, '{}', '')",
            (cohort, token, event_type, key, ts, ts),
        )
        c.commit()


def test_config_json_overrides_defaults(db_mod, tmp_path, monkeypatch):
    """With default blocked_min=10, an event 3 min ago does NOT trigger blocked.
    With a config file setting blocked_min=2, the same event DOES trigger blocked."""
    # Step 1 : default — no blocked alert
    import monitor
    monitor._config_reset_cache()
    _insert_event(db_mod, "c1", "tok-cfg", "hint_revealed", "xss", minutes_ago=3)
    alerts_default = monitor.compute_alerts(db_mod, "c1")
    assert all(a["kind"] != "blocked" or a["student_token"] != "tok-cfg" for a in alerts_default)

    # Step 2 : write config with blocked_min=2, reset cache, re-run
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"monitor": {"blocked_min": 2}}), encoding="utf-8")
    monkeypatch.setenv("DASHBOARD_CONFIG_JSON", str(config_file))
    monitor._config_reset_cache()

    alerts_overridden = monitor.compute_alerts(db_mod, "c1")
    blocked_for_tok = [a for a in alerts_overridden if a["kind"] == "blocked" and a["student_token"] == "tok-cfg"]
    assert len(blocked_for_tok) == 1, f"Expected 1 blocked alert with override, got {alerts_overridden}"
