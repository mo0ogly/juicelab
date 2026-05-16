"""JuiceLab teacher dashboard.

Receives pedagogical events emitted by juicelab-overlay running inside
Juice Shop instances, stores them in SQLite, and exposes a teacher view
that summarises cohort progress.

Environment variables:
    DASHBOARD_TEACHER_TOKEN   shared secret required to read /dashboard
                              and admin endpoints. Required at boot.
    DASHBOARD_PROOF_SECRET    HMAC-SHA256 secret (>=16 chars) used to sign
                              tamper-evident lab proofs. Required for
                              /api/proof to be active. Should be kept
                              server-side and shared with verify_proof.py.
    DASHBOARD_DB              path to the sqlite file (default: ./data/dashboard.sqlite)
    DASHBOARD_PORT            HTTP port (default: 5000)
    DASHBOARD_CORS_ORIGINS    comma-separated allow-list, default:
                              http://127.0.0.1:3000,http://localhost:3000
                              In docker-compose the per-instance hostnames
                              are added at deploy time.

Routes:
    POST /api/sync            ingest a SyncEvent from the plugin
    GET  /api/health          liveness probe
    GET  /dashboard           HTML cohort summary, gated by token
    GET  /api/cohort          JSON cohort summary, same gating
    GET  /api/proof           signed lab proof (.md) for one student+challenge

The shape of SyncEvent matches the TypeScript interface in
frontend/src/app/juicelab-overlay/models/juicelab.types.ts.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import hmac
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

import requests
import secrets

from flask import Flask, Response, g, jsonify, render_template, request
from flask_cors import CORS

from db import (cohort_exists, count_pending_award_events, count_team_mappings,
    ensure_cohort, ensure_student, get_connection, get_team_mapping, init_schema,
    names_for_cohort, mark_award_pushed, pending_award_events, set_team_mapping,
    tags_for_cohort)
from cohorts_routes import register_cohorts_routes; from join_routes import register_join_routes; from sync_routes import register_sync_routes; from i18n_helpers import register_i18n; from proof_routes import register_proof_routes; from csrf import check_csrf, clear_csrf_cookie, issue_csrf_token, set_csrf_cookie; from audit_log import log_event; from sse_routes import register_sse_routes; from tags_routes import register_tags_routes; from monitor import start_monitor, persist_alert; from alerts_routes import register_alerts_routes
from students_routes import register_students_routes
from diploma_routes import register_diploma_routes; from pdf_routes import register_pdf_routes

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("DASHBOARD_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)

ALLOWED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "session_start",
        "session_end",
        "hint_revealed",
        "challenge_solved",
        "journal_filled",
        "quiz_completed",
        "badge_earned",
        "flag_verified",
    }
)


def _ctf_secret() -> str:
    """Shared HMAC secret used by Juice Shop CTF mode to compute flags.
    Set via JUICESHOP_CTF_SECRET env var. Must match the secret on the
    Juice Shop side (config/default.yml application.id is the canonical
    Juice Shop variable, but its CTF flag formula is HMAC over the key
    using this shared secret in the official juice-shop-ctf-cli)."""
    return os.environ.get("JUICESHOP_CTF_SECRET", "")


def _expected_flag(challenge_name: str) -> str:
    """Replicate Juice Shop's lib/utils.ts ctfFlag() : HMAC-SHA1 of the
    challenge.name (NOT challenge.key) with the shared CTF_KEY."""
    secret = _ctf_secret()
    if not secret or not challenge_name:
        return ""
    mac = hmac.new(secret.encode("utf-8"), challenge_name.encode("utf-8"), hashlib.sha1)
    return mac.hexdigest()


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "DASHBOARD_CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


def _teacher_token() -> str:
    token = os.environ.get("DASHBOARD_TEACHER_TOKEN", "")
    if len(token) < 16:
        LOGGER.warning(
            "DASHBOARD_TEACHER_TOKEN is missing or shorter than 16 chars; "
            "/dashboard will refuse all requests"
        )
    return token


def _proof_secret() -> bytes:
    raw = os.environ.get("DASHBOARD_PROOF_SECRET", "")
    if len(raw) < 16:
        return b""
    return raw.encode("utf-8")


# ---- CTFd integration (Mode C, opt-in) -----------------------------------
#
# When CTFD_URL and CTFD_ADMIN_TOKEN env vars are set, every hint_revealed
# event triggers a negative award POST to the central CTFd. The leaderboard
# then reflects the pedagogical effort (an N5-spammer is visibly penalised)
# instead of just rewarding flag-paste speed. When env vars are absent
# (Mode A standalone or Mode B cohort tracking without competition), every
# CTFd helper below is a no-op and the dashboard behaves exactly as before.

_CTFD_LAST_ERROR: str = ""


def _ctfd_url() -> str:
    return os.environ.get("CTFD_URL", "").rstrip("/")


def _ctfd_token() -> str:
    return os.environ.get("CTFD_ADMIN_TOKEN", "")


def _ctfd_enabled() -> bool:
    return bool(_ctfd_url()) and bool(_ctfd_token())


def _ctfd_team_mode() -> str:
    """Either 'team' (CTFd team mode, push awards to a team_id) or 'user'
    (push to a user_id). Default 'team' matches the CTFd 3.7 default."""
    raw = os.environ.get("CTFD_TEAM_MODE", "team").strip().lower()
    return "user" if raw == "user" else "team"


def _ctfd_penalty_formula() -> str:
    raw = os.environ.get("CTFD_PENALTY_FORMULA", "mirror_juicelab").strip().lower()
    return raw if raw in {"mirror_juicelab", "uniform_10pct"} else "mirror_juicelab"


def _ctfd_request(
    method: str, path: str, *, json_body: dict[str, Any] | None = None
) -> requests.Response | None:
    """Wrap requests with the CTFd auth header and a tight timeout. Returns
    None on misconfiguration or network failure (the caller treats None as
    a soft failure that leaves award_pushed_at NULL for later reconcile)."""
    global _CTFD_LAST_ERROR
    base = _ctfd_url()
    token = _ctfd_token()
    if not base or not token:
        return None
    url = base + path
    headers = {
        "Authorization": "Token " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = requests.request(
            method, url, headers=headers, json=json_body, timeout=5.0
        )
    except requests.RequestException as exc:
        _CTFD_LAST_ERROR = f"{type(exc).__name__}: {exc}"
        LOGGER.warning("CTFd %s %s unreachable: %s", method, path, exc)
        return None
    if resp.status_code >= 400:
        _CTFD_LAST_ERROR = f"HTTP {resp.status_code}: {resp.text[:200]}"
        LOGGER.warning("CTFd %s %s -> HTTP %s", method, path, resp.status_code)
    else:
        _CTFD_LAST_ERROR = ""
    return resp


def _resolve_ctfd_team(
    student_token: str, cohort_id: str, email: str | None
) -> tuple[int | None, int | None]:
    """Return (team_id, user_id). Either may be None depending on the
    CTFd team mode and whether the student has registered yet. The mapping
    is cached per student_token after the first successful resolution.
    A row with NULL team_id is NOT cached (we want to retry on the next
    hint event)."""
    with get_connection() as conn:
        cached = get_team_mapping(conn, student_token)
    if cached is not None and (cached[0] is not None or cached[1] is not None):
        return cached

    if not email:
        return (None, None)

    team_id: int | None = None
    user_id: int | None = None

    # Try teams first when team mode is active. CTFd 3.7 lists teams via
    # /api/v1/teams ; we filter client-side because the public list may not
    # accept arbitrary query params on every install.
    if _ctfd_team_mode() == "team":
        resp = _ctfd_request("GET", "/api/v1/teams?per_page=200")
        if resp is not None and resp.status_code == 200:
            payload = _safe_json(resp)
            for team in payload.get("data", []) or []:
                team_email = (team.get("email") or "").strip().lower()
                if team_email == email.strip().lower():
                    team_id = int(team.get("id")) if team.get("id") is not None else None
                    break

    # Always try users — even in team mode we use the user_id as a fallback
    # so a student without a team can still receive awards if CTFd allows.
    resp = _ctfd_request(
        "GET", "/api/v1/users?q=" + email + "&field=email&per_page=20"
    )
    if resp is not None and resp.status_code == 200:
        payload = _safe_json(resp)
        for user in payload.get("data", []) or []:
            user_email = (user.get("email") or "").strip().lower()
            if user_email == email.strip().lower():
                user_id = int(user.get("id")) if user.get("id") is not None else None
                if team_id is None and user.get("team_id") is not None:
                    team_id = int(user["team_id"])
                break

    if team_id is not None or user_id is not None:
        with get_connection() as conn:
            set_team_mapping(
                conn,
                student_token,
                team_id,
                user_id,
                datetime.now(timezone.utc).isoformat(),
            )

    return (team_id, user_id)


def _safe_json(resp: requests.Response) -> dict[str, Any]:
    try:
        body = resp.json()
        return body if isinstance(body, dict) else {}
    except (ValueError, requests.exceptions.JSONDecodeError):
        return {}


def _compute_penalty_value(cost_pct: int) -> int:
    """Translate the juicelab hint cost (5/10/20/35/50) into a negative
    CTFd award value. mirror_juicelab maps cost_pct directly to negative
    points; uniform_10pct ignores the level and returns -10."""
    formula = _ctfd_penalty_formula()
    if formula == "uniform_10pct":
        return -10
    # mirror_juicelab : -cost_pct (e.g. N5 with cost_pct=50 -> -50pts)
    return -abs(int(cost_pct))


def _push_hint_penalty(
    event_id: int,
    student_token: str,
    cohort_id: str,
    challenge_key: str | None,
    hint_level: str,
    cost_pct: int,
    student_email: str | None,
) -> bool:
    """POST a negative award to CTFd to reflect the juicelab hint reveal.
    Returns True on confirmed push (events.award_pushed_at is stamped),
    False otherwise (silently — caller does not raise). Best-effort: any
    network or auth failure leaves the row with award_pushed_at NULL so a
    future /api/admin/reconcile-awards run can retry it."""
    if not _ctfd_enabled():
        return False
    team_id, user_id = _resolve_ctfd_team(student_token, cohort_id, student_email)
    if team_id is None and user_id is None:
        LOGGER.info(
            "CTFd: no team/user mapped for %s yet (email=%s), award queued",
            student_token,
            student_email,
        )
        return False

    value = _compute_penalty_value(cost_pct)
    body: dict[str, Any] = {
        "name": f"Hint {hint_level} on {challenge_key or 'unknown'}",
        "value": value,
        "category": challenge_key or "juicelab",
        "description": (
            f"Penalty for revealing hint level {hint_level} "
            f"({cost_pct}% of juicelab score)"
        ),
    }
    if _ctfd_team_mode() == "team" and team_id is not None:
        body["team_id"] = team_id
    elif user_id is not None:
        body["user_id"] = user_id
    elif team_id is not None:
        body["team_id"] = team_id
    else:
        return False

    resp = _ctfd_request("POST", "/api/v1/awards", json_body=body)
    if resp is None or resp.status_code >= 400:
        return False
    with get_connection() as conn:
        mark_award_pushed(conn, event_id, datetime.now(timezone.utc).isoformat())
    return True


def _maybe_push_award_for_event(
    event_id: int, payload: dict[str, Any]
) -> None:
    """Hook called by _insert_event after a successful INSERT. Wrapped in
    a broad try/except so a CTFd outage never breaks event ingestion."""
    if not _ctfd_enabled():
        return
    if payload.get("event_type") != "hint_revealed":
        return
    data = payload.get("data") or {}
    level = data.get("level") or ""
    cost_pct = data.get("cost_pct")
    if not isinstance(level, str) or not isinstance(cost_pct, (int, float)):
        LOGGER.debug("CTFd: skipping malformed hint_revealed event %d", event_id)
        return
    # The student email lives inside SyncEvent.data (not at the top level)
    # so it survives in events.data_json and a /reconcile-awards run can
    # rebuild the CTFd team mapping after a restart. Frontend juicelab-sync
    # injects it on hint_revealed events specifically.
    email = data.get("student_email")
    if not isinstance(email, str):
        email = None
    try:
        _push_hint_penalty(
            event_id=event_id,
            student_token=str(payload["student_token"]).strip(),
            cohort_id=str(payload["cohort_id"]).strip(),
            challenge_key=payload.get("challenge_key"),
            hint_level=level,
            cost_pct=int(cost_pct),
            student_email=email,
        )
    except Exception:  # pragma: no cover - safety net
        LOGGER.exception("CTFd push hook crashed for event %d", event_id)


def _events_for(student_token: str, challenge_key: str, cohort_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_type, data_json, client_ts, server_ts, instance_label
              FROM events
             WHERE student_token = ? AND challenge_key = ? AND cohort_id = ?
             ORDER BY id ASC
            """,
            (student_token, challenge_key, cohort_id),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            data = json.loads(r["data_json"]) if r["data_json"] else {}
        except json.JSONDecodeError:
            data = {}
        out.append({
            "event_type": str(r["event_type"]),
            "data": data,
            "client_ts": str(r["client_ts"]),
            "server_ts": str(r["server_ts"]),
            "instance_label": r["instance_label"],
        })
    return out



def _check_teacher_auth() -> tuple[bool, Response | None]:
    expected = _teacher_token()
    if not expected:
        return False, (jsonify({"error": "dashboard disabled (token not set)"}), 503)  # type: ignore[return-value]
    provided = (
        request.headers.get("X-Teacher-Token", "")
        or request.cookies.get("teacher_token", "")
    )
    if not hmac.compare_digest(provided, expected):
        log_event("login_fail", source="api"); return False, (jsonify({"error": "invalid teacher token"}), 401)  # type: ignore[return-value]
    if not check_csrf():
        log_event("csrf_fail"); return False, (jsonify({"error": "invalid or missing csrf token"}), 403)  # type: ignore[return-value]
    return True, None


def _check_teacher_auth_html() -> tuple[bool, Response | None]:
    """Same as _check_teacher_auth but redirects to /login when missing."""
    expected = _teacher_token()
    if not expected:
        return False, (Response("<h1>Dashboard disabled</h1><p>DASHBOARD_TEACHER_TOKEN env var is missing.</p>", status=503, content_type="text/html; charset=utf-8"))  # type: ignore[return-value]
    provided = (
        request.headers.get("X-Teacher-Token", "")
        or request.cookies.get("teacher_token", "")
    )
    if not hmac.compare_digest(provided, expected):
        from flask import redirect, url_for  # local import to avoid top-level redirect cost
        target = request.full_path or "/dashboard"
        return False, redirect(f"/login?next={target}")  # type: ignore[return-value]
    return True, None


def _validate_event(payload: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload must be a JSON object"
    student = payload.get("student_token")
    if not isinstance(student, str) or not student.strip():
        return False, "student_token required and non-empty"
    cohort = payload.get("cohort_id")
    if not isinstance(cohort, str) or not cohort.strip():
        return False, "cohort_id required and non-empty"
    event_type = payload.get("event_type")
    if event_type not in ALLOWED_EVENT_TYPES:
        return False, f"event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}"
    if "challenge_key" in payload and payload["challenge_key"] is not None:
        if not isinstance(payload["challenge_key"], str):
            return False, "challenge_key must be a string when present"
    if "data" in payload and not isinstance(payload["data"], dict):
        return False, "data must be a JSON object"
    if not isinstance(payload.get("client_timestamp", ""), str):
        return False, "client_timestamp must be a string"
    return True, ""


def _insert_event(payload: dict[str, Any], instance_label: str | None) -> int:
    server_ts = datetime.now(timezone.utc).isoformat()
    data_json = json.dumps(payload.get("data", {}), ensure_ascii=False, sort_keys=True)
    tok, coh = payload["student_token"].strip(), payload["cohort_id"].strip()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO events (student_token, cohort_id, event_type, challenge_key, "
            "data_json, client_ts, server_ts, instance_label) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tok, coh, payload["event_type"], payload.get("challenge_key"),
             data_json, payload.get("client_timestamp", server_ts), server_ts, instance_label),
        )
        new_id = int(cur.lastrowid or 0)
        ensure_cohort(conn, coh, server_ts); ensure_student(conn, coh, tok, server_ts)

    # CTFd Mode C hook : best-effort push of the hint penalty to the central
    # CTFd. No-op in Mode A / Mode B (env vars absent). Wrapped at the
    # callsite so any failure here never propagates to the ingest endpoint.
    _maybe_push_award_for_event(new_id, payload)
    return new_id


def _cohort_summary(cohort_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        # Only surface events that belong to a student still registered in
        # the roster. Without this, the matrix shows orphan tokens left
        # behind by /api/students DELETE (which keeps events for audit)
        # or by test recettes that emit events under throwaway tokens.
        # The matrix should match /admin/students by definition.
        rows = conn.execute(
            """
            SELECT e.student_token, e.event_type, e.challenge_key, e.data_json, e.client_ts
              FROM events e
             WHERE e.cohort_id = ?
               AND e.student_token IN (
                   SELECT student_token FROM students WHERE cohort_id = ?
               )
             ORDER BY e.id ASC
            """,
            (cohort_id, cohort_id),
        ).fetchall()

    students: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    challenge_keys: set[str] = set()
    # Total events per student, including session_start / connection events
    # that have no challenge_key. Used to surface activity in the matrix
    # row even before the student touches a real challenge.
    event_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        student = str(row["student_token"])
        challenge = row["challenge_key"]
        event_type = str(row["event_type"])
        # Ensure student appears in roster even if no challenge yet
        _ = students[student]
        event_counts[student] += 1
        if challenge:
            challenge_keys.add(str(challenge))
            slot = students[student].setdefault(
                str(challenge),
                {
                    "hints": 0,
                    "journal": False,
                    "quiz_score": None,
                    "solved": False,
                    "flag_verified": False,
                    "last_ts": None,
                },
            )
            try:
                data = json.loads(row["data_json"]) if row["data_json"] else {}
            except json.JSONDecodeError:
                data = {}
            if event_type == "hint_revealed":
                slot["hints"] = max(int(slot["hints"]), len(data.get("consumed_levels") or []) or int(slot["hints"]) + 1)
            elif event_type == "journal_filled":
                slot["journal"] = True
            elif event_type == "quiz_completed":
                score = data.get("score")
                if isinstance(score, int):
                    slot["quiz_score"] = score
            elif event_type == "challenge_solved":
                slot["solved"] = True
            elif event_type == "flag_verified":
                slot["flag_verified"] = True
            slot["last_ts"] = row["client_ts"]

    sorted_students = sorted(students.keys())
    sorted_challenges = sorted(challenge_keys)

    # Aggregate the per-student final score : average over challenges that
    # have at least a quiz score, using the same formula as the proof
    # ((100 - sum_costs + quiz) / 2) per challenge then averaged.
    totals: dict[str, dict[str, Any]] = {}
    cost_map = {1: 5, 2: 15, 3: 35, 4: 70, 5: 120}
    for student in sorted_students:
        per_chall = students[student]
        sums: list[int] = []; partials: list[int] = []; chall_done = 0
        for slot in per_chall.values():
            score_chall = max(0, 100 - cost_map.get(int(slot.get("hints") or 0), int(slot.get("hints") or 0) * 5))
            quiz = slot.get("quiz_score")
            if isinstance(quiz, int):
                bonus = 10 if slot.get("flag_verified") else 0
                sums.append(min(100, (score_chall + quiz) // 2 + bonus)); chall_done += 1
            else:
                partials.append(score_chall)
        avg = round(sum(sums) / len(sums)) if sums else None
        partial = round(sum(partials) / len(partials)) if partials else None
        totals[student] = {"avg_score": avg, "partial_score": partial,
            "challenges_with_quiz": chall_done, "challenges_touched": len(per_chall)}

    with get_connection() as conn:
        roster = names_for_cohort(conn, cohort_id)
        tags = tags_for_cohort(conn, cohort_id)
    return {
        "cohort_id": cohort_id, "students": sorted_students,
        "challenges": sorted_challenges,
        "matrix": {s: students[s] for s in sorted_students},
        "totals": totals, "events_total": len(rows),
        "event_counts": {s: event_counts.get(s, 0) for s in sorted_students},
        "names": {t: roster[t] for t in sorted_students if t in roster},
        "tags": tags,
    }


def _compute_css_sri(filename: str = "dashboard.css") -> str:
    """SHA-384 SRI hash per .css file (each <link> needs its own digest;
    @import-loaded sub-files inherit no SRI from parent)."""
    css_path = Path(__file__).parent / "static" / filename
    try:
        digest = hashlib.sha384(css_path.read_bytes()).digest()
    except OSError:
        return ""
    return "sha384-" + base64.b64encode(digest).decode("ascii")


_CSS_SRI = _compute_css_sri("dashboard.css")
_CSS_WIDGETS_SRI = _compute_css_sri("dashboard-widgets.css")


def create_app() -> Flask:
    """Application factory used by the dev server and pytest."""
    init_schema()
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": _cors_origins()}},
         allow_headers=["Content-Type", "Authorization", "X-Teacher-Token", "X-Instance-Label", "X-Student-Token"],
         methods=["GET", "POST", "DELETE", "OPTIONS"])
    register_i18n(app); register_students_routes(app, _check_teacher_auth, _check_teacher_auth_html); register_cohorts_routes(app, _check_teacher_auth, _check_teacher_auth_html); register_join_routes(app); register_sync_routes(app, _validate_event, _insert_event); register_proof_routes(app, _check_teacher_auth, expected_flag=_expected_flag, insert_event=_insert_event, events_for=_events_for, proof_secret=_proof_secret); register_diploma_routes(app, _check_teacher_auth_html, _check_teacher_auth, proof_secret=_proof_secret); register_sse_routes(app, _check_teacher_auth, _cohort_summary); register_tags_routes(app, _check_teacher_auth); register_alerts_routes(app, _check_teacher_auth); register_pdf_routes(app, _check_teacher_auth, _cohort_summary)
    if os.environ.get("DASHBOARD_MONITOR_ENABLED", "1").strip() != "0": import db as _dbm; start_monitor(_dbm, lambda a: persist_alert(_dbm, a))

    @app.before_request
    def _csp_nonce() -> None:
        # Per-request nonce: lets us drop script-src 'unsafe-inline' while
        # keeping inline <script nonce="..."> blocks that emit the i18n catalog.
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def _inject_csp_nonce() -> dict:
        return {"csp_nonce": getattr(g, "csp_nonce", ""), "css_sri": _CSS_SRI, "css_widgets_sri": _CSS_WIDGETS_SRI}

    @app.after_request
    def _security_headers(resp: Response) -> Response:
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "interest-cohort=()")
        # HSTS only when explicitly opted in (DASHBOARD_HTTPS=true). Setting
        # it on a plain-HTTP origin would force every visitor's browser to
        # upgrade subsequent requests to HTTPS without a valid cert, breaking
        # the deployment. See docs/VPS_HARDENING.md before enabling.
        if os.environ.get("DASHBOARD_HTTPS", "false").lower() == "true":
            resp.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        nonce = getattr(g, "csp_nonce", "")
        script_src = f"'self' 'nonce-{nonce}' 'strict-dynamic'" if nonce else "'self'"
        resp.headers.setdefault("Content-Security-Policy",
            f"default-src 'self'; "
            f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            f"font-src 'self' https://fonts.gstatic.com; "
            f"script-src {script_src}; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")
        # Note: Server header neutralization happens at WSGI handler level
        # (see WSGIRequestHandler patch below the app factory) because
        # Flask's after_request only stacks alongside Werkzeug's own header.
        resp.headers["Cache-Control"] = resp.headers.get("Cache-Control") or "no-store"
        return resp

    @app.get("/api/health")
    def health() -> Response:
        return jsonify({"ok": True, "ts": datetime.now(timezone.utc).isoformat()})

    @app.get("/api/cohort")
    def api_cohort() -> Response:
        ok, err = _check_teacher_auth()
        if not ok and err is not None:
            return err
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return jsonify({"error": "missing cohort query parameter"}), 400  # type: ignore[return-value]
        return jsonify(_cohort_summary(cohort))

    @app.get("/login")
    def login_form() -> Response:
        nxt = request.args.get("next", "/dashboard")
        return Response(
            render_template("login.html", next=nxt, error=""),
            content_type="text/html; charset=utf-8",
        )

    @app.post("/login")
    def login_submit() -> Response:
        from flask import redirect, make_response  # local imports
        expected = _teacher_token()
        if not expected:
            return Response("<h1>Dashboard disabled</h1>", status=503, content_type="text/html; charset=utf-8")
        provided = (request.form.get("token") or "").strip()
        nxt = (request.form.get("next") or "/dashboard").strip()
        if not hmac.compare_digest(provided, expected):
            log_event("login_fail", source="form")
            return Response(
                render_template("login.html", next=nxt, error="Token incorrect."),
                status=401,
                content_type="text/html; charset=utf-8",
            )
        # Cookie httponly, samesite=lax, no expiry (session) — teacher closes
        # browser to logout, or hits /logout explicitly.
        resp = make_response(redirect(nxt))
        resp.set_cookie(
            "teacher_token",
            expected,
            httponly=True,
            samesite="Lax",
            secure=(os.environ.get("DASHBOARD_HTTPS", "false").lower() == "true"),
            path="/",
        )
        set_csrf_cookie(resp, issue_csrf_token())
        log_event("login_success")
        return resp

    @app.get("/logout")
    def logout() -> Response:
        from flask import redirect, make_response
        resp = make_response(redirect("/login"))
        resp.delete_cookie("teacher_token", path="/")
        clear_csrf_cookie(resp)
        return resp

    @app.get("/dashboard")
    def dashboard() -> Response:
        from flask import redirect
        ok, err = _check_teacher_auth_html()
        if not ok and err is not None:
            return err
        # Cohort comes from the query param ?cohort=... ; fallback chain :
        # explicit query > DASHBOARD_DEFAULT_COHORT env var > redirect to
        # /admin/cohorts so the prof can pick one (no more bare 400 page).
        cohort = (
            request.args.get("cohort", "").strip()
            or os.environ.get("DASHBOARD_DEFAULT_COHORT", "").strip()
        )
        if not cohort:
            return redirect("/admin/cohorts?reason=pick", code=302)  # type: ignore[return-value]
        # Validate the cohort actually exists. Silent "empty matrix" when
        # someone hits /dashboard?cohort=DELETED is confusing : surface a
        # friendly 404 with a clear escape route.
        with get_connection() as conn:
            if not cohort_exists(conn, cohort):
                return Response(
                    render_template(
                        "dashboard_404.html",
                        cohort_id=cohort,
                    ),
                    status=404,
                    content_type="text/html; charset=utf-8",
                )
        summary = _cohort_summary(cohort)
        return Response(
            render_template("dashboard.html", summary=summary),
            content_type="text/html; charset=utf-8",
        )

    @app.get("/api/admin/ctfd-status")
    def api_admin_ctfd_status() -> Response:
        ok, err = _check_teacher_auth()
        if not ok and err is not None:
            return err
        enabled = _ctfd_enabled()
        with get_connection() as conn:
            teams = count_team_mappings(conn)
            pending = count_pending_award_events(conn)
        return jsonify({
            "enabled": enabled,
            "ctfd_url": _ctfd_url() or None,
            "team_mode": _ctfd_team_mode(),
            "penalty_formula": _ctfd_penalty_formula(),
            "teams_mapped": teams,
            "pending_pushes": pending,
            "last_error": _CTFD_LAST_ERROR or None,
        })

    @app.post("/api/admin/reconcile-awards")
    def api_admin_reconcile_awards() -> Response:
        ok, err = _check_teacher_auth()
        if not ok and err is not None:
            return err
        if not _ctfd_enabled():
            return jsonify({
                "error": "CTFd push disabled (CTFD_URL or CTFD_ADMIN_TOKEN missing)",
                "retried": 0,
                "succeeded": 0,
                "failed": 0,
            }), 503  # type: ignore[return-value]

        with get_connection() as conn:
            rows = pending_award_events(conn)

        retried = 0
        succeeded = 0
        failed = 0
        for row in rows:
            retried += 1
            try:
                data = json.loads(row["data_json"]) if row["data_json"] else {}
            except json.JSONDecodeError:
                data = {}
            level = data.get("level") or ""
            cost_pct = data.get("cost_pct")
            if not isinstance(level, str) or not isinstance(cost_pct, (int, float)):
                failed += 1
                continue
            # Reconcile cannot fish out the email post-hoc — the team
            # mapping must already be cached or the row is left pending.
            email = data.get("student_email")
            ok_push = _push_hint_penalty(
                event_id=int(row["id"]),
                student_token=row["student_token"],
                cohort_id=row["cohort_id"],
                challenge_key=row["challenge_key"],
                hint_level=level,
                cost_pct=int(cost_pct),
                student_email=email,
            )
            if ok_push:
                succeeded += 1
            else:
                failed += 1

        return jsonify({"retried": retried, "succeeded": succeeded, "failed": failed})

    return app


if __name__ == "__main__":  # pragma: no cover
    # Mask Werkzeug version in Server header (info disclosure mitigation).
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.server_version = "JuiceLab"
    WSGIRequestHandler.sys_version = ""
    port = int(os.environ.get("DASHBOARD_PORT", "5000"))
    app = create_app()
    app.run(host=os.environ.get("DASHBOARD_BIND", "0.0.0.0"), port=port, debug=False)  # noqa: S104 nosec B104 (binding overridable; production deploys must set DASHBOARD_BIND=127.0.0.1 + reverse proxy, see docs/VPS_HARDENING.md)
