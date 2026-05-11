"""Lightweight i18n for the Flask dashboard (prof side).

Catalogues live under dashboard/i18n/<lang>.json. The active language is
resolved per request from (in order):

1. URL query param ?lang=fr|en (sets cookie for next requests)
2. Cookie dash_lang
3. Header Accept-Language
4. Default 'fr'

Templates use the Jinja filter `t('KEY', placeholder=value)` to translate.
The resolved lang is exposed as `current_lang` and the full active catalog
is exposed as `i18n_catalog` so client-side JS can pick up labels too.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from flask import Flask, Response, g, request

LOGGER = logging.getLogger(__name__)

SUPPORTED = ("fr", "en")
DEFAULT_LANG = "fr"
COOKIE_NAME = "dash_lang"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

I18N_DIR = Path(__file__).parent / "i18n"
_CATALOGS: dict[str, dict[str, str]] = {}


def _load_catalog(lang: str) -> dict[str, str]:
    """Read and cache a catalog. Falls back to empty dict if file missing
    (caller-side t() falls back to the default lang then the key itself)."""
    if lang in _CATALOGS:
        return _CATALOGS[lang]
    path = I18N_DIR / f"{lang}.json"
    if not path.is_file():
        LOGGER.warning("i18n catalog missing for lang=%s at %s", lang, path)
        _CATALOGS[lang] = {}
        return _CATALOGS[lang]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.error("i18n catalog parse failure for %s: %s", lang, exc)
        data = {}
    _CATALOGS[lang] = data
    return data


def _resolve_lang() -> str:
    """Pick the active language for the current request.

    URL takes precedence so a teacher can switch language without touching
    settings; the choice is then persisted via cookie at response time.
    """
    q = (request.args.get("lang") or "").strip().lower()
    if q in SUPPORTED:
        return q
    c = (request.cookies.get(COOKIE_NAME) or "").strip().lower()
    if c in SUPPORTED:
        return c
    # Accept-Language fallback: take the best match among SUPPORTED.
    accepts = request.accept_languages
    if accepts:
        match = accepts.best_match(list(SUPPORTED))
        if match:
            return match
    return DEFAULT_LANG


def _translate(key: str, **fmt: Any) -> str:
    """Return the translated string for the current request lang. Falls back
    to the default language catalog, then to the literal key if both miss.
    Format placeholders are str.format'ed in if provided."""
    lang = getattr(g, "current_lang", DEFAULT_LANG)
    cat = _load_catalog(lang)
    txt = cat.get(key)
    if txt is None and lang != DEFAULT_LANG:
        txt = _load_catalog(DEFAULT_LANG).get(key)
    if txt is None:
        return key
    if fmt:
        try:
            return txt.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return txt
    return txt


def register_i18n(app: Flask) -> None:
    """Wire the resolver, the Jinja filter, the context processor, and the
    cookie persistence hook. Call once from create_app()."""

    @app.before_request
    def _set_lang():
        g.current_lang = _resolve_lang()

    @app.after_request
    def _persist_cookie(response: Response) -> Response:
        # Only set the cookie when the user explicitly asks for a lang
        # change via ?lang=, so we do not clobber an existing pref.
        q = (request.args.get("lang") or "").strip().lower()
        if q in SUPPORTED:
            response.set_cookie(
                COOKIE_NAME, q,
                max_age=COOKIE_MAX_AGE,
                httponly=False,  # accessible to JS so client banners can flip too
                samesite="Lax",
            )
        return response

    @app.context_processor
    def _inject():
        lang = getattr(g, "current_lang", DEFAULT_LANG)
        return {
            "t": _translate,
            "current_lang": lang,
            "i18n_catalog": _load_catalog(lang),
        }

    # Jinja filter form so {{ 'KEY' | t }} works too.
    app.jinja_env.filters["t"] = _translate
