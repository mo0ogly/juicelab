"""Endpoints for HMAC-signed lab proofs + journal text + CTF flag check.

Extracted from app.py to keep the main file under the 800-line limit
enforced by .claude/hooks/file_size_check.cjs. The handlers themselves
are unchanged ; only their wiring has moved.

Endpoints registered :
  POST /api/verify-flag    public, HMAC compares the submitted CTF flag
                           against the secret-derived expected value.
  GET  /api/journal-text   gated, returns the latest journal_filled
                           (phase=after) event text for one student.
  GET  /api/proof          public via DASHBOARD_PROOF_SECRET, returns
                           an HMAC-signed Markdown proof file for one
                           student + challenge + cohort.

All shared helpers (_expected_flag, _events_for, _insert_event, ...)
stay in app.py and are injected at register-time, mirroring the
pattern used by sync_routes.register_sync_routes.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Flask, Response, jsonify, render_template, request  # noqa: F401

LOGGER = logging.getLogger(__name__)

AuthFn = Callable[[], "tuple[bool, Any]"]


def build_proof_markdown(
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

    last: dict[str, dict[str, Any]] = {}
    for ev in events:
        last[ev["event_type"]] = ev

    journal_text = {"after": ""}
    journal_ts = {"after": ""}
    quiz_data: dict[str, Any] = {}
    quiz_ts = ""
    hints_consumed: list[tuple[str, int, str]] = []
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


def sign_proof(body: str, *, secret: bytes, student_token: str, challenge_key: str) -> str:
    """Append the signed footer to a proof body. Returns the full document."""
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


def register_proof_routes(
    app: Flask,
    auth_check_json: AuthFn,
    *,
    expected_flag: Callable[[str], str],
    insert_event: Callable[[dict[str, Any], "str | None"], int],
    events_for: Callable[[str, str, str], list[dict[str, Any]]],
    proof_secret: Callable[[], bytes],
) -> None:

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

        expected = expected_flag(challenge_name)
        if not expected:
            return jsonify({"error": "flag verification disabled (JUICESHOP_CTF_SECRET missing)", "valid": False}), 503  # type: ignore[return-value]

        valid = hmac.compare_digest(expected, submitted)
        if valid:
            insert_event({
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
        ok, err = auth_check_json()
        if not ok and err is not None:
            return err
        student_token = (request.args.get("student_token") or "").strip()
        cohort_id = (request.args.get("cohort") or "").strip()
        challenge_key = (request.args.get("key") or "").strip()
        if not (student_token and cohort_id and challenge_key):
            return jsonify({"error": "missing student_token, cohort or key"}), 400  # type: ignore[return-value]
        events = events_for(student_token, challenge_key, cohort_id)
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
        if not proof_secret():
            return jsonify({"error": "proof signing disabled (DASHBOARD_PROOF_SECRET missing)"}), 503  # type: ignore[return-value]
        events = events_for(student_token, challenge_key, cohort_id)
        if not events:
            return jsonify({"error": "no events for this student/challenge/cohort"}), 404  # type: ignore[return-value]
        secret_bytes = proof_secret()
        body = build_proof_markdown(
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
            doc = sign_proof(body, secret=secret_bytes, student_token=student_token, challenge_key=challenge_key)
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
