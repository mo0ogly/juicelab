"""Coverage : rate_limit.ip_key + rate_limit decorator.

Pure-Python tests using a minimal Flask app instead of the full dashboard,
to avoid bucket pollution from other recettes and to control the time
boundary explicitly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rate_limit import ip_key, rate_limit, _buckets


@pytest.fixture(autouse=True)
def _clear_buckets():
    _buckets.clear()
    yield
    _buckets.clear()


@pytest.fixture
def app_with_limiter():
    app = Flask(__name__)

    @app.get("/ping")
    @rate_limit(ip_key, max_calls=3, window_sec=60)
    def ping():
        return jsonify({"ok": True})

    return app.test_client()


def test_ip_key_uses_xff(app_with_limiter):
    with app_with_limiter.application.test_request_context(
        "/ping", headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    ):
        assert ip_key() == "203.0.113.7"


def test_ip_key_falls_back_to_remote_addr(app_with_limiter):
    with app_with_limiter.application.test_request_context(
        "/ping", environ_overrides={"REMOTE_ADDR": "192.0.2.42"}
    ):
        assert ip_key() == "192.0.2.42"


def test_ip_key_rejects_oversized_xff(app_with_limiter):
    long_ip = "1" * 200
    with app_with_limiter.application.test_request_context(
        "/ping",
        headers={"X-Forwarded-For": long_ip},
        environ_overrides={"REMOTE_ADDR": "10.0.0.1"},
    ):
        key = ip_key()
        assert key != long_ip
        assert len(key) <= 64


def test_ip_key_empty_xff_falls_back(app_with_limiter):
    with app_with_limiter.application.test_request_context(
        "/ping",
        headers={"X-Forwarded-For": ""},
        environ_overrides={"REMOTE_ADDR": "10.0.0.99"},
    ):
        assert ip_key() == "10.0.0.99"


def test_ip_key_no_remote_addr(app_with_limiter):
    with app_with_limiter.application.test_request_context(
        "/ping", environ_overrides={"REMOTE_ADDR": None}
    ):
        assert ip_key() == "?"


def test_rate_limit_allows_within_quota(app_with_limiter):
    for _ in range(3):
        r = app_with_limiter.get("/ping")
        assert r.status_code == 200


def test_rate_limit_blocks_after_quota(app_with_limiter):
    for _ in range(3):
        app_with_limiter.get("/ping")
    r = app_with_limiter.get("/ping")
    assert r.status_code == 429
    body = r.get_json()
    assert body["error"] == "rate limit exceeded"
    assert body["retry_after_sec"] >= 0


def test_rate_limit_isolates_by_ip(app_with_limiter):
    for _ in range(3):
        app_with_limiter.get("/ping", headers={"X-Forwarded-For": "203.0.113.1"})
    r_ip1 = app_with_limiter.get("/ping", headers={"X-Forwarded-For": "203.0.113.1"})
    r_ip2 = app_with_limiter.get("/ping", headers={"X-Forwarded-For": "203.0.113.2"})
    assert r_ip1.status_code == 429
    assert r_ip2.status_code == 200


def test_rate_limit_isolates_by_endpoint():
    app = Flask(__name__)

    @app.get("/a")
    @rate_limit(ip_key, max_calls=2, window_sec=60)
    def a():
        return jsonify({"r": "a"})

    @app.get("/b")
    @rate_limit(ip_key, max_calls=2, window_sec=60)
    def b():
        return jsonify({"r": "b"})

    c = app.test_client()
    c.get("/a"); c.get("/a")
    r_a = c.get("/a")
    r_b = c.get("/b")
    assert r_a.status_code == 429
    assert r_b.status_code == 200


def test_rate_limit_window_slides(monkeypatch):
    import rate_limit as rl

    app = Flask(__name__)
    fake_time = [1000.0]

    def fake_monotonic():
        return fake_time[0]

    monkeypatch.setattr(rl.time, "monotonic", fake_monotonic)

    @app.get("/slide")
    @rate_limit(ip_key, max_calls=2, window_sec=60)
    def slide():
        return jsonify({"ok": True})

    c = app.test_client()
    fake_time[0] = 1000.0
    assert c.get("/slide").status_code == 200
    assert c.get("/slide").status_code == 200
    assert c.get("/slide").status_code == 429

    fake_time[0] = 1061.0
    assert c.get("/slide").status_code == 200
