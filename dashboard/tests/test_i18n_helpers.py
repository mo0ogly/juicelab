"""Coverage : i18n_helpers _resolve_lang / _translate / cookie persistence.

Exercises every branch of the 4-tier lang resolver (URL > cookie >
Accept-Language > default) plus the catalog fallback (current lang
missing key -> default lang -> literal key) and the format-error
swallow path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import i18n_helpers as i18n


@pytest.fixture(autouse=True)
def _clear_catalogs():
    i18n._CATALOGS.clear()
    yield
    i18n._CATALOGS.clear()


@pytest.fixture
def wired_app():
    app = Flask(__name__)
    i18n.register_i18n(app)

    @app.get("/echo")
    def echo():
        from flask import g
        return jsonify({"lang": g.current_lang, "hello": app.jinja_env.filters["t"]("WELCOME_PROF_DASHBOARD_TITLE")})

    return app.test_client()


# --- _load_catalog -------------------------------------------------------

def test_load_catalog_fr_returns_dict():
    cat = i18n._load_catalog("fr")
    assert isinstance(cat, dict)
    assert len(cat) > 0


def test_load_catalog_en_returns_dict():
    cat = i18n._load_catalog("en")
    assert isinstance(cat, dict)
    assert len(cat) > 0


def test_load_catalog_missing_returns_empty():
    cat = i18n._load_catalog("zz-unknown")
    assert cat == {}


def test_load_catalog_cached():
    a = i18n._load_catalog("fr")
    b = i18n._load_catalog("fr")
    assert a is b


def test_load_catalog_parse_failure(tmp_path, monkeypatch):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(i18n, "I18N_DIR", tmp_path)
    cat = i18n._load_catalog("broken")
    assert cat == {}


# --- _resolve_lang -------------------------------------------------------

def test_resolve_lang_url_wins(wired_app):
    r = wired_app.get("/echo?lang=en")
    assert r.get_json()["lang"] == "en"


def test_resolve_lang_invalid_url_falls_back(wired_app):
    r = wired_app.get("/echo?lang=zz")
    assert r.get_json()["lang"] == "fr"


def test_resolve_lang_cookie(wired_app):
    wired_app.set_cookie("dash_lang", "en")
    r = wired_app.get("/echo")
    assert r.get_json()["lang"] == "en"


def test_resolve_lang_accept_language(wired_app):
    r = wired_app.get("/echo", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert r.get_json()["lang"] == "en"


def test_resolve_lang_default(wired_app):
    r = wired_app.get("/echo")
    assert r.get_json()["lang"] == "fr"


def test_resolve_lang_cookie_overrides_accept_language(wired_app):
    wired_app.set_cookie("dash_lang", "fr")
    r = wired_app.get("/echo", headers={"Accept-Language": "en"})
    assert r.get_json()["lang"] == "fr"


# --- _translate ----------------------------------------------------------

def test_translate_known_key_returns_translation():
    app = Flask(__name__)
    i18n.register_i18n(app)
    with app.test_request_context("/?lang=en"):
        from flask import g
        g.current_lang = "en"
        out = i18n._translate("LANG_NAME")
        assert out == "English"


def test_translate_unknown_key_returns_literal():
    app = Flask(__name__)
    i18n.register_i18n(app)
    with app.test_request_context("/"):
        from flask import g
        g.current_lang = "fr"
        assert i18n._translate("THIS_KEY_DOES_NOT_EXIST_ANYWHERE") == "THIS_KEY_DOES_NOT_EXIST_ANYWHERE"


def test_translate_fallback_to_default_lang():
    app = Flask(__name__)
    i18n.register_i18n(app)
    fr = i18n._load_catalog("fr")
    sample_key = next(iter(fr.keys()))
    i18n._CATALOGS["en"] = {}
    with app.test_request_context("/?lang=en"):
        from flask import g
        g.current_lang = "en"
        out = i18n._translate(sample_key)
        assert out == fr[sample_key]


def test_translate_format_substitutes():
    app = Flask(__name__)
    i18n.register_i18n(app)
    i18n._CATALOGS["fr"] = {"HELLO_NAME": "Bonjour {name}"}
    with app.test_request_context("/"):
        from flask import g
        g.current_lang = "fr"
        assert i18n._translate("HELLO_NAME", name="Alice") == "Bonjour Alice"


def test_translate_format_error_swallowed():
    app = Flask(__name__)
    i18n.register_i18n(app)
    i18n._CATALOGS["fr"] = {"REQUIRES_MORE": "Bonjour {nom} {age}"}
    with app.test_request_context("/"):
        from flask import g
        g.current_lang = "fr"
        out = i18n._translate("REQUIRES_MORE", nom="Alice")
        # Format failure must return the raw template, not crash.
        assert "Bonjour" in out


# --- after_request cookie persistence -----------------------------------

def test_lang_cookie_set_when_url_param(wired_app):
    r = wired_app.get("/echo?lang=en")
    sc = r.headers.get("Set-Cookie", "")
    assert "dash_lang=en" in sc


def test_lang_cookie_not_set_without_url_param(wired_app):
    r = wired_app.get("/echo")
    sc = r.headers.get("Set-Cookie", "")
    assert "dash_lang=" not in sc


def test_lang_cookie_https_secure(monkeypatch):
    monkeypatch.setenv("DASHBOARD_HTTPS", "true")
    app = Flask(__name__)
    i18n.register_i18n(app)

    @app.get("/x")
    def x():
        return "ok"

    c = app.test_client()
    r = c.get("/x?lang=en")
    assert "Secure" in r.headers.get("Set-Cookie", "")
