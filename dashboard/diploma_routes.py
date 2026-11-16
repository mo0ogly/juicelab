"""End-of-cohort diploma generation, registry and verification.

Mirrors the proof_routes signing pattern but operates at cohort level :
one diploma per student summarising their entire TD performance,
HMAC-SHA256 signed under DASHBOARD_PROOF_SECRET with a distinct scheme
("diploma.v2") so a forged challenge-proof can never pose as a diploma.

Figures : diploma_scores.diploma_figures (per-challenge scores, as on the
challenge proofs, averaged over solved challenges ; mention from
progression and final score).

Registry : a diploma is issued on first request (page or ZIP), stored in
the ``diplomas`` table (db_diplomas) and then served as stored, so a
reprint has the same date and signature. When the student's results changed
since issuance the page says so ; the teacher re-issues explicitly, which
adds a new registry row.

Endpoints registered :
  GET  /admin/diploma/<token>?cohort=X           print-ready page (A4)
  POST /api/diplomas/<token>/reissue?cohort=X    issue a new diploma from
                                                 current results
  GET  /api/diplomas.zip?cohort=X                every eligible student's
                                                 diploma as .md (validated
                                                 students ; "participation"
                                                 skipped unless include_all=1)

Verifiability : the signed footer embeds STUDENT, COHORT, MENTION,
PROGRESS_PCT, FINAL_SCORE, TIMESTAMP (issuance). Whoever holds
DASHBOARD_PROOF_SECRET recomputes the HMAC over the body up to the
SIGNATURE line (dashboard/verify_proof.py). diploma.v1 documents (footer
field SCORE_PCT = progression) still verify.
"""

from __future__ import annotations

import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Callable

import hashlib
import hmac
from flask import Flask, Response, jsonify, render_template, request

from db import get_connection, list_students, per_student_stats
from db_diplomas import count_issuances, insert_diploma, latest_diploma
from diploma_scores import diploma_figures
from learning_story import challenge_stories
from session_report import cohort_events

LOGGER = logging.getLogger(__name__)

AuthFn = Callable[[], "tuple[bool, Any]"]
SCHEME = "diploma.v2"


def _institution() -> str:
    """Issuing institution name. Configurable via env so a different
    school can re-brand without touching templates."""
    return os.environ.get("DASHBOARD_INSTITUTION", "M2 IA - Sorbonne Universite")


def sign_diploma(body: str, *, secret: bytes, student_token: str, cohort_id: str,
                 mention: str, progress_pct: int, final_score: int | None,
                 issued_at: str) -> str:
    """Append the signed footer to a diploma body.

    ``issued_at`` (ISO) is the issuance date, signed as TIMESTAMP ;
    ``final_score`` None is written "none". Raises RuntimeError without
    secret. Distinct SCHEME from proof_routes.sign_proof so a forged
    challenge proof cannot be repackaged as a diploma."""
    if not secret:
        raise RuntimeError("DASHBOARD_PROOF_SECRET missing or shorter than 16 chars")
    footer_lines = [
        "---",
        "DIPLOMA: HMAC-SHA256",
        "SCHEME: " + SCHEME,
        "TIMESTAMP: " + issued_at,
        "STUDENT: " + student_token,
        "COHORT: " + cohort_id,
        "MENTION: " + mention,
        "PROGRESS_PCT: " + str(progress_pct),
        "FINAL_SCORE: " + ("none" if final_score is None else str(final_score)),
    ]
    signed_payload = body + "\n" + "\n".join(footer_lines) + "\n"
    sig = hmac.new(secret, signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return signed_payload + "SIGNATURE: " + sig + "\n"


def _pct(v: int | None) -> str:
    return "_non calculable_" if v is None else "**" + str(v) + "/100**"


def build_diploma_md(*, student_token: str, student_name: str, cohort_id: str,
                     institution: str, figures: dict[str, Any], td_total: int) -> str:
    """Markdown body up to (but not including) the signed footer.

    ``figures`` comes from diploma_scores.diploma_figures plus
    ``journals_written`` / ``journal_words``. Same content drives the ZIP
    batch (.md per student) and the HTML page verification block."""
    f = figures
    quiz = ("| Moyenne quiz (challenges resolus) | " + _pct(f["quiz_pct"])
            + (" ; " + str(f["quiz_missing"]) + " resolu(s) sans quiz, compte(s) 0" if f["quiz_missing"] else "")
            + " |")
    retex = ("| Journaux retex rediges | **" + str(f["journals_written"]) + "** ("
             + str(f["journal_words"]) + " mots cumules) |"
             if f["journals_written"] > 0 else "| Journaux retex rediges | _aucun journal redige_ |")
    lines = [
        "# Diplome - " + cohort_id, "",
        "Decerne par : **" + institution + "**", "",
        "## Recipiendaire", "",
        "| Champ | Valeur |", "|---|---|",
        "| Nom | " + (student_name or "_(non renseigne)_") + " |",
        "| Token UUID | `" + student_token + "` |",
        "| Cohorte | " + cohort_id + " |", "",
        "## Mention obtenue", "",
        "**" + f["mention"].replace("_", " ").upper() + "**", "",
        "## Resultats consolides", "",
        "| Indicateur | Valeur |", "|---|---|",
        "| Progression challenges | **" + str(f["progress_pct"]) + "%** ("
        + str(f["challenges_solved"]) + "/" + str(td_total) + " resolus) |",
        "| Score challenge moyen (apres indices) | " + _pct(f["score_challenge"]) + " |",
        quiz,
        "| Flags CTF verifies | " + str(f["flags_verified"]) + " |",
        "| Indices consommes | " + str(f["hints_used"]) + " (tous challenges) |",
        retex, "",
        "## Score final", "",
        "Par challenge resolu : score_final = min(100, (score_challenge + score_quiz) / 2 + bonus_flag), "
        "avec score_challenge = 100 - couts des indices de CE challenge, score_quiz = 0 si quiz non soumis, "
        "bonus_flag = +10 si flag CTF verifie. Le score final du diplome est la moyenne sur les challenges resolus.",
        "",
        "Score final : " + _pct(f["final_score"]), "",
        "Mention : progression >= 80 % et score final >= 70 : tres bien ; >= 60 % et >= 60 : bien ; "
        "progression >= 40 % : reussite ; sinon participation.", "",
        "## Verification", "",
        "Ce diplome est tamper-evident : la signature HMAC-SHA256 ci-dessous "
        "couvre tout le corps du document. Toute alteration invalide la "
        "signature (verifier via `python dashboard/verify_proof.py`).", "",
    ]
    return "\n".join(lines)


def _gather_diploma_context(conn: Any, cohort_id: str, td_total: int = 13) -> dict[str, Any]:
    """Current figures of every roster student : token -> {display_name,
    status, figures}. Figures are recomputed from the event log on each
    call (diploma_scores.diploma_figures + journal counters)."""
    stats = {r["student_token"]: r for r in per_student_stats(conn, cohort_id)}
    by_token: dict[str, list] = {}
    for ev in cohort_events(conn, cohort_id):
        by_token.setdefault(ev["student_token"], []).append(ev)
    out: dict[str, dict[str, Any]] = {}
    for s in list_students(conn, cohort_id):
        tok = s["student_token"]
        figures = diploma_figures(challenge_stories(by_token.get(tok, [])), td_total)
        stat = stats.get(tok)
        figures["journals_written"] = int(stat["journals_written"] or 0) if stat else 0
        figures["journal_words"] = int(stat["journal_word_total"] or 0) if stat else 0
        out[tok] = {
            "display_name": s["display_name"],
            "status": s["status"] if "status" in s.keys() else "validated",
            "figures": json.loads(json.dumps(figures)),
        }
    return out


def _issue(conn: Any, cohort_id: str, token: str, ctx: dict[str, Any],
           secret: bytes, *, td_total: int = 13) -> dict[str, Any]:
    """Sign the current figures, record them, return the stored diploma."""
    issued_at = datetime.now(timezone.utc).isoformat()
    f = ctx["figures"]
    body = build_diploma_md(student_token=token, student_name=ctx["display_name"] or "",
                            cohort_id=cohort_id, institution=_institution(),
                            figures=f, td_total=td_total)
    signed = sign_diploma(body, secret=secret, student_token=token, cohort_id=cohort_id,
                          mention=f["mention"], progress_pct=f["progress_pct"],
                          final_score=f["final_score"], issued_at=issued_at)
    insert_diploma(conn, cohort_id=cohort_id, student_token=token,
                   issued_at=issued_at, figures=f, signed_body=signed)
    conn.commit()
    return latest_diploma(conn, cohort_id, token)  # type: ignore[return-value]


def _stored_or_issue(conn: Any, cohort_id: str, token: str, ctx: dict[str, Any],
                     secret: bytes) -> dict[str, Any]:
    """Latest stored diploma, issuing the first one when there is none."""
    return latest_diploma(conn, cohort_id, token) or _issue(conn, cohort_id, token, ctx, secret)


def register_diploma_routes(
    app: Flask,
    auth_check_html: AuthFn,
    auth_check_json: AuthFn,
    *,
    proof_secret: Callable[[], bytes],
) -> None:

    @app.get("/admin/diploma/<token>")
    def diploma_html(token: str) -> Response:
        """Stored diploma page ; issues it on first view. 400 without
        cohort, 503 without signing secret, 404 for a student outside the
        cohort roster."""
        ok, err = auth_check_html()
        if not ok and err is not None:
            return err
        cohort_id = (request.args.get("cohort") or "").strip()
        if not cohort_id:
            return Response("missing cohort", status=400)
        if not proof_secret():
            return Response("diploma signing disabled (DASHBOARD_PROOF_SECRET missing)", status=503)
        with get_connection() as conn:
            ctx = _gather_diploma_context(conn, cohort_id).get(token)
            if not ctx:
                return Response("student not found in cohort", status=404)
            dip = _stored_or_issue(conn, cohort_id, token, ctx, proof_secret())
            issuances = count_issuances(conn, cohort_id, token)
        return Response(
            render_template(
                "diploma.html",
                cohort_id=cohort_id, student_token=token,
                student_name=ctx["display_name"] or "",
                f=dip["figures"], td_total=13,
                institution=_institution(),
                signed_body=dip["signed_body"],
                issued_at=dip["issued_at"][:10],
                issuances=issuances,
                stale=dip["figures"] != ctx["figures"],
            ),
            content_type="text/html; charset=utf-8",
        )

    @app.post("/api/diplomas/<token>/reissue")
    def diploma_reissue(token: str) -> Response:
        """Issue a new diploma from current results (new registry row ; the
        previous ones stay recorded). JSON {ok, issued_at, mention}."""
        ok, err = auth_check_json()
        if not ok and err is not None:
            return err
        cohort_id = (request.args.get("cohort") or "").strip()
        if not cohort_id:
            return jsonify({"error": "missing cohort"}), 400  # type: ignore[return-value]
        if not proof_secret():
            return jsonify({"error": "diploma signing disabled"}), 503  # type: ignore[return-value]
        with get_connection() as conn:
            ctx = _gather_diploma_context(conn, cohort_id).get(token)
            if not ctx:
                return jsonify({"error": "student not found in cohort"}), 404  # type: ignore[return-value]
            dip = _issue(conn, cohort_id, token, ctx, proof_secret())
        return jsonify({"ok": True, "issued_at": dip["issued_at"], "mention": dip["mention"]})

    @app.get("/api/diplomas.zip")
    def diplomas_zip() -> Response:
        """Stored diplomas of validated students (issuing missing ones),
        skipping stored "participation" unless include_all=1."""
        ok, err = auth_check_json()
        if not ok and err is not None:
            return err
        cohort_id = (request.args.get("cohort") or "").strip()
        if not cohort_id:
            return Response("missing cohort", status=400)
        include_all = request.args.get("include_all", "0").lower() in ("1", "true", "yes")
        if not proof_secret():
            return Response("diploma signing disabled", status=503)
        buf = io.BytesIO()
        written = 0
        with get_connection() as conn:
            ctx_all = _gather_diploma_context(conn, cohort_id)
            if not ctx_all:
                return Response("no students in cohort", status=404)
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for token, ctx in ctx_all.items():
                    if ctx["status"] != "validated":
                        continue
                    stored = latest_diploma(conn, cohort_id, token)
                    mention = stored["mention"] if stored else ctx["figures"]["mention"]
                    if not include_all and mention == "participation":
                        continue
                    dip = stored or _issue(conn, cohort_id, token, ctx, proof_secret())
                    safe = (ctx["display_name"] or token).replace("/", "_").replace(" ", "_")
                    zf.writestr(f"{dip['mention']}_{safe[:60]}.md", dip["signed_body"])
                    written += 1
        if written == 0:
            return Response("no eligible diplomas in cohort (set include_all=1 to force)", status=404)
        buf.seek(0)
        filename = f"diplomas_{cohort_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
        return Response(
            buf.read(),
            content_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
