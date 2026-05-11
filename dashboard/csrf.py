"""CSRF protection via double-submit cookie.

The double-submit cookie pattern is a stateless CSRF defence that fits
the dashboard's existing cookie-based teacher session :

1. On a successful /login response, the server issues an additional
   cookie ``csrf_token`` containing a random hex value. The cookie is
   intentionally readable by JS (``HttpOnly=False``) so the dashboard
   templates can echo its value back as the ``X-CSRF-Token`` header.

2. Every state-changing request (POST / PUT / DELETE / PATCH) on a
   gated route MUST carry the ``X-CSRF-Token`` header. The server
   compares it (timing-safe) to the value of the ``csrf_token`` cookie.
   A mismatch returns 403.

3. Cross-site form posts and XHRs cannot read the cookie because of
   the same-origin policy, so the attacker cannot forge a matching
   header. SameSite=Lax on both the auth cookie and the CSRF cookie
   also blocks navigated cross-site POSTs.

The public student-facing endpoints (``/api/cohort/join``,
``/api/student/status``, ``/api/cohort/exists``, ``/api/sync``,
``/api/verify-flag``) are deliberately NOT CSRF-gated : they are
designed to be called from arbitrary Juice Shop instances and have
their own rate-limit + server-side status gate in lieu of session
binding.

References : OWASP "Cross-Site Request Forgery Prevention" cheat sheet,
section "Synchronizer Token Pattern" + "Double Submit Cookie".
"""

from __future__ import annotations

import hmac
import os
import secrets

from flask import Response, request

COOKIE_NAME = "csrf_token"
HEADER_NAME = "X-CSRF-Token"
COOKIE_MAX_AGE = 60 * 60 * 12  # 12 hours, matches a teaching day


def issue_csrf_token() -> str:
    """Return a fresh 32-byte hex token (256 bits of entropy)."""
    return secrets.token_hex(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Attach the CSRF token cookie to a response. Called after /login."""
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=False,  # readable by JS so the dashboard templates can echo it
        samesite="Lax",
        secure=(os.environ.get("DASHBOARD_HTTPS", "false").lower() == "true"),
        path="/",
    )


def clear_csrf_cookie(response: Response) -> None:
    """Remove the CSRF token cookie. Called by /logout."""
    response.delete_cookie(COOKIE_NAME, path="/")


def check_csrf() -> bool:
    """Return True if the current request passes the double-submit check.

    Read-only methods (GET / HEAD / OPTIONS) are always allowed.

    API clients that authenticate via the ``X-Teacher-Token`` header
    (CLI tools, automated recettes, server-to-server calls) are
    EXEMPT from CSRF : they are not subject to the cross-site
    request-forgery threat model since no browser session is
    involved and the attacker has no way to set the
    ``X-Teacher-Token`` header from a third-party origin.

    Browser sessions (auth via the ``teacher_token`` cookie) MUST
    carry a non-empty ``X-CSRF-Token`` header that matches the
    ``csrf_token`` cookie via ``hmac.compare_digest``.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    # API client path : header-based auth is CSRF-immune.
    if request.headers.get("X-Teacher-Token"):
        return True
    header = (request.headers.get(HEADER_NAME) or "").strip()
    cookie = (request.cookies.get(COOKIE_NAME) or "").strip()
    if not header or not cookie:
        return False
    return hmac.compare_digest(header, cookie)
