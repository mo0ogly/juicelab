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

import hashlib
import hmac
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

import requests
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

from db import (count_pending_award_events, count_team_mappings, ensure_cohort, ensure_student,
    get_connection, get_team_mapping, init_schema, names_for_cohort,
    mark_award_pushed, pending_award_events, set_team_mapping)
from cohorts_routes import register_cohorts_routes; from join_routes import register_join_routes; from sync_routes import register_sync_routes; from i18n_helpers import register_i18n
from students_routes import register_students_routes

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


def _build_proof_markdown(
    *,
    student_token: str,
    student_name: str,
    cohort_id: str,
    challenge_key: str,
    challenge_name: str,
    challenge_category: str,
    challenge_difficulty: int,
    challenge_description: str,
    events: list[dict[str, Any]],
) -> str:
    """Compose the markdown body up to (but not including) the SIGNATURE line."""
    lines: list[str] = []
    push = lines.append

    # Pick the latest event of each type to reflect final state.
    last: dict[str, dict[str, Any]] = {}
    for ev in events:
        last[ev["event_type"]] = ev

    journal_text = {"after": ""}
    journal_ts = {"after": ""}
    quiz_data: dict[str, Any] = {}
    quiz_ts = ""
    hints_consumed: list[tuple[str, int, str]] = []  # (level, cost_pct, ts)
    solved_ts = ""
    flag_verified = False
    flag_ts = ""

    for ev in events:
        et = ev["event_type"]
        d = ev["data"]
        ts = ev["client_ts"] or ev["server_ts"]
        if et == "journal_filled":
            phase = d.get("phase")
            txt = d.get("text", "")
            # The "before" phase no longer exists in the UI (replaced by the
            # read-only Briefing tab). Only "after" entries are kept.
            if phase == "after" and isinstance(txt, str):
                journal_text["after"] = txt
                journal_ts["after"] = ts
        elif et == "quiz_completed":
            quiz_data = d
            quiz_ts = ts
        elif et == "hint_revealed":
            lvl = str(d.get("level", "?"))
            cost = int(d.get("cost_pct", 0)) if isinstance(d.get("cost_pct"), (int, float)) else 0
            hints_consumed.append((lvl, cost, ts))
        elif et == "challenge_solved":
            solved_ts = ts
        elif et == "flag_verified":
            flag_verified = True
            flag_ts = ts

    score_after_hints = 100 - sum(c for _, c, _ in hints_consumed)
    if score_after_hints < 0:
        score_after_hints = 0

    push("# JuiceLab proof - " + (challenge_name or challenge_key))
    push("")
    push("| Champ | Valeur |")
    push("|---|---|")
    push("| Etudiant | " + (student_name or "_(non renseigne)_") + " |")
    push("| Challenge key | `" + challenge_key + "` |")
    push("| Categorie | " + (challenge_category or "-") + " |")
    push("| Difficulte | " + (str(challenge_difficulty) + "/6" if challenge_difficulty else "-") + " |")
    push("| Cohorte | " + cohort_id + " |")
    push("| Token (UUID) | `" + student_token + "` |")
    push("")

    if challenge_description:
        push("## Brief")
        push("")
        push(challenge_description.strip())
        push("")

    push("## Journal de l'etudiant")
    push("")
    push((journal_text["after"] or "_(vide)_").strip())
    push("")
    if journal_ts["after"]:
        push("_Saisi le " + journal_ts["after"] + "_")
        push("")

    push("## Indices consommes")
    push("")
    if not hints_consumed:
        push("_aucun_")
    else:
        push("| Niveau | Cout (%) | Horodatage |")
        push("|---|---|---|")
        for lvl, cost, ts in hints_consumed:
            push("| " + lvl + " | " + str(cost) + " | " + ts + " |")
        push("")
        push("Score apres indices : **" + str(score_after_hints) + "/100**")
    push("")

    push("## Quiz")
    push("")
    if not quiz_data:
        push("_Quiz pas encore soumis_")
        score_quiz_value = None
    else:
        score = quiz_data.get("score")
        score_quiz_value = int(score) if isinstance(score, (int, float)) else None
        push("Score quiz : **" + (str(score_quiz_value) if score_quiz_value is not None else "-") + "/100**")
        push("")
        answers = quiz_data.get("answers") or {}
        bq = {
            "Q1": quiz_data.get("q1_score"),
            "Q2": quiz_data.get("q2_score"),
            "Q3": quiz_data.get("q3_score"),
        }
        push("| Question | Reponse | Score |")
        push("|---|---|---|")
        for q in ("Q1", "Q2", "Q3"):
            ans = answers.get(q, "-")
            sc = bq.get(q)
            push("| " + q + " | " + str(ans) + " | " + (str(sc) if sc is not None else "-") + " |")
        if quiz_ts:
            push("")
            push("_Soumis le " + quiz_ts + "_")
    push("")

    # Score final : moyenne 50/50 entre score challenge (apres indices) et
    # score quiz, plus un bonus +10 plafonne a 100 si le flag CTF a ete
    # verifie. Si le quiz n'a pas ete soumis, on n'agrege pas — on affiche
    # les deux composantes brutes pour eviter de noter sur du vide.
    push("## Score final")
    push("")
    push("**Formule** : score_final = min(100, (score_challenge + score_quiz) / 2 + bonus_flag)")
    push("")
    push("- score_challenge = 100 - somme des couts d'indices = **" + str(score_after_hints) + "/100**")
    if score_quiz_value is None:
        push("- score_quiz = _quiz pas encore soumis, score final non calculable_")
        push("")
        bonus_line = " (+10 flag CTF verifie)" if flag_verified else ""
        partial = min(100, score_after_hints + (10 if flag_verified else 0))
        push("Score final partiel : **" + str(partial) + "/100** (composante challenge seule" + bonus_line + ")")
    else:
        avg = round((score_after_hints + score_quiz_value) / 2)
        bonus = 10 if flag_verified else 0
        final = min(100, avg + bonus)
        push("- score_quiz = **" + str(score_quiz_value) + "/100**")
        push("- bonus_flag = **+" + str(bonus) + "** (flag CTF " + ("verifie" if flag_verified else "non soumis") + ")")
        push("")
        push("Score final : **" + str(final) + "/100**")
    push("")

    push("## Trace")
    push("")
    push("| Evenement | Timestamp |")
    push("|---|---|")
    push("| Resolution Juice Shop | " + (solved_ts or "non resolu") + " |")
    push("| Export proof | " + datetime.now(timezone.utc).isoformat() + " |")
    push("")

    return "\n".join(lines)


def _sign_proof(body: str, *, student_token: str, challenge_key: str) -> str:
    """Append the signed footer to a proof body. Returns the full document."""
    secret = _proof_secret()
    if not secret:
        raise RuntimeError("DASHBOARD_PROOF_SECRET missing or shorter than 16 chars")
    footer_lines = [
        "---",
        "PROOF: HMAC-SHA256",
        "SCHEME: v1",
        "TIMESTAMP: " + datetime.now(timezone.utc).isoformat(),
        "STUDENT: " + student_token,
        "CHALLENGE: " + challenge_key,
    ]
    signed_payload = body + "\n" + "\n".join(footer_lines) + "\n"
    sig = hmac.new(secret, signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return signed_payload + "SIGNATURE: " + sig + "\n"


def _check_teacher_auth() -> tuple[bool, Response | None]:
    expected = _teacher_token()
    if not expected:
        return False, (jsonify({"error": "dashboard disabled (token not set)"}), 503)  # type: ignore[return-value]
    provided = (
        request.headers.get("X-Teacher-Token", "")
        or request.cookies.get("teacher_token", "")
    )
    if provided != expected:
        return False, (jsonify({"error": "invalid teacher token"}), 401)  # type: ignore[return-value]
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
    if provided != expected:
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
        rows = conn.execute(
            """
            SELECT student_token, event_type, challenge_key, data_json, client_ts
              FROM events
             WHERE cohort_id = ?
             ORDER BY id ASC
            """,
            (cohort_id,),
        ).fetchall()

    students: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    challenge_keys: set[str] = set()

    for row in rows:
        student = str(row["student_token"])
        challenge = row["challenge_key"]
        event_type = str(row["event_type"])
        # Ensure student appears in roster even if no challenge yet
        _ = students[student]
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
    for student in sorted_students:
        per_chall = students[student]
        sums: list[int] = []
        chall_done = 0
        for ch_key, slot in per_chall.items():
            hints = int(slot.get("hints") or 0)
            cost_map = {1: 5, 2: 15, 3: 35, 4: 70, 5: 120}
            cost = cost_map.get(hints, hints * 5)
            score_chall = max(0, 100 - cost)
            quiz = slot.get("quiz_score")
            if isinstance(quiz, int):
                base = (score_chall + quiz) // 2
                bonus = 10 if slot.get("flag_verified") else 0
                sums.append(min(100, base + bonus))
                chall_done += 1
        avg = round(sum(sums) / len(sums)) if sums else None
        totals[student] = {"avg_score": avg, "challenges_with_quiz": chall_done}

    with get_connection() as conn: roster = names_for_cohort(conn, cohort_id)
    return {
        "cohort_id": cohort_id, "students": sorted_students,
        "challenges": sorted_challenges,
        "matrix": {s: students[s] for s in sorted_students},
        "totals": totals, "events_total": len(rows),
        "names": {t: roster[t] for t in sorted_students if t in roster},
    }


def create_app() -> Flask:
    """Application factory used by the dev server and pytest."""
    init_schema()
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": _cors_origins()}},
         allow_headers=["Content-Type", "Authorization", "X-Teacher-Token", "X-Instance-Label", "X-Student-Token"],
         methods=["GET", "POST", "DELETE", "OPTIONS"])
    register_i18n(app); register_students_routes(app, _check_teacher_auth, _check_teacher_auth_html); register_cohorts_routes(app, _check_teacher_auth, _check_teacher_auth_html); register_join_routes(app); register_sync_routes(app, _validate_event, _insert_event)

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

    @app.post("/api/verify-flag")
    def api_verify_flag() -> Response:
        if not request.is_json:
            return jsonify({"error": "expected application/json body"}), 400  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        student_token = str(payload.get("student_token") or "").strip()
        cohort_id = str(payload.get("cohort_id") or "").strip()
        challenge_key = str(payload.get("challenge_key") or "").strip()
        challenge_name = str(payload.get("challenge_name") or "").strip()
        submitted = str(payload.get("flag") or "").strip().lower()
        if not (student_token and cohort_id and challenge_key and challenge_name and submitted):
            return jsonify({"error": "missing student_token, cohort_id, challenge_key, challenge_name or flag"}), 400  # type: ignore[return-value]

        expected = _expected_flag(challenge_name)
        if not expected:
            return jsonify({"error": "flag verification disabled (JUICESHOP_CTF_SECRET missing)", "valid": False}), 503  # type: ignore[return-value]

        valid = hmac.compare_digest(expected, submitted)
        if valid:
            # Persist as event so the dashboard matrix and the proof can
            # reflect the +10 bonus.
            _insert_event({
                "student_token": student_token,
                "cohort_id": cohort_id,
                "event_type": "flag_verified",
                "challenge_key": challenge_key,
                "data": {"bonus_pts": 10},
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
            }, request.headers.get("X-Instance-Label") or None)
        return jsonify({"valid": valid})

    @app.get("/api/journal-text")
    def api_journal_text() -> Response:
        ok, err = _check_teacher_auth()
        if not ok and err is not None:
            return err
        student_token = (request.args.get("student_token") or "").strip()
        cohort_id = (request.args.get("cohort") or "").strip()
        challenge_key = (request.args.get("key") or "").strip()
        if not (student_token and cohort_id and challenge_key):
            return jsonify({"error": "missing student_token, cohort or key"}), 400  # type: ignore[return-value]

        events = _events_for(student_token, challenge_key, cohort_id)
        # Pick the latest journal_filled with phase=after.
        latest_text = ""
        latest_ts = ""
        latest_words = None
        for ev in events:
            if ev["event_type"] != "journal_filled":
                continue
            d = ev["data"]
            if d.get("phase") != "after":
                continue
            if isinstance(d.get("text"), str):
                latest_text = d["text"]
                latest_ts = ev["client_ts"] or ev["server_ts"]
                latest_words = d.get("word_count")
        return jsonify({
            "student_token": student_token,
            "challenge_key": challenge_key,
            "cohort_id": cohort_id,
            "text": latest_text,
            "last_ts": latest_ts,
            "word_count": latest_words,
        })

    @app.get("/api/proof")
    def api_proof() -> Response:
        student_token = (request.args.get("student_token") or request.headers.get("X-Student-Token") or "").strip()
        student_name = (request.args.get("student_name") or "").strip()
        cohort_id = (request.args.get("cohort") or "").strip()
        challenge_key = (request.args.get("key") or "").strip()
        if not student_token:
            return jsonify({"error": "missing student_token"}), 400  # type: ignore[return-value]
        if not cohort_id:
            return jsonify({"error": "missing cohort"}), 400  # type: ignore[return-value]
        if not challenge_key:
            return jsonify({"error": "missing key"}), 400  # type: ignore[return-value]
        if not _proof_secret():
            return jsonify({"error": "proof signing disabled (DASHBOARD_PROOF_SECRET missing)"}), 503  # type: ignore[return-value]

        events = _events_for(student_token, challenge_key, cohort_id)
        if not events:
            return jsonify({"error": "no events for this student/challenge/cohort"}), 404  # type: ignore[return-value]

        body = _build_proof_markdown(
            student_token=student_token,
            student_name=student_name,
            cohort_id=cohort_id,
            challenge_key=challenge_key,
            challenge_name=request.args.get("name", challenge_key),
            challenge_category=request.args.get("category", ""),
            challenge_difficulty=int(request.args.get("difficulty") or 0),
            challenge_description=request.args.get("description", ""),
            events=events,
        )
        try:
            doc = _sign_proof(body, student_token=student_token, challenge_key=challenge_key)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503  # type: ignore[return-value]

        filename = "juicelab-{key}-{ts}.md".format(
            key=challenge_key,
            ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        )
        resp = Response(doc, content_type="text/markdown; charset=utf-8")
        resp.headers["Content-Disposition"] = 'attachment; filename="' + filename + '"'
        resp.headers["Cache-Control"] = "no-store"
        return resp

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
        if provided != expected:
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
            secure=False,  # set True if dashboard is served over HTTPS
            path="/",
        )
        return resp

    @app.get("/logout")
    def logout() -> Response:
        from flask import redirect, make_response
        resp = make_response(redirect("/login"))
        resp.delete_cookie("teacher_token", path="/")
        return resp

    @app.get("/dashboard")
    def dashboard() -> Response:
        ok, err = _check_teacher_auth_html()
        if not ok and err is not None:
            return err
        # Cohort comes from the query param ?cohort=... ; fallback chain :
        # explicit query > DASHBOARD_DEFAULT_COHORT env var > 400 error.
        cohort = (
            request.args.get("cohort", "").strip()
            or os.environ.get("DASHBOARD_DEFAULT_COHORT", "").strip()
        )
        if not cohort:
            return Response(
                "<h1>JuiceLab dashboard</h1>"
                "<p>Manque <code>?cohort=&lt;id&gt;</code> dans l'URL "
                "ou la variable d'environnement <code>DASHBOARD_DEFAULT_COHORT</code>.</p>",
                status=400,
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
    port = int(os.environ.get("DASHBOARD_PORT", "5000"))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False)
