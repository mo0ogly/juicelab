"""End-of-cohort diploma generation and verification.

Mirrors the proof_routes signing pattern but operates at cohort level :
one diploma per student summarising their entire TD performance,
HMAC-SHA256 signed under DASHBOARD_PROOF_SECRET with a distinct scheme
("diploma.v1") so a forged challenge-proof can never pose as a diploma.

Endpoints registered :
  GET /admin/diploma/<token>?cohort=X       HTML print-ready page (A4)
                                            with HMAC-signed verification
                                            block at the bottom.
  GET /api/diplomas.zip?cohort=X            ZIP batch of every eligible
                                            student's diploma as
                                            individual .md files,
                                            same HMAC scheme.

Eligibility (mention auto) :
  - "tres bien"  : >= 80% challenges solved AND >= 70% quiz average
  - "bien"       : >= 60% challenges solved AND >= 60% quiz average
  - "reussite"   : >= 40% challenges solved
  - none         : below 40% solved, diploma still produced if the
                   prof requests it explicitly (mention="participation")

The teacher decides whether to issue a low-mention diploma : the per-
student HTML endpoint always renders, the batch ZIP filter defaults to
mention != "participation" but accepts ?include_all=1.

Verifiability : the signed footer embeds STUDENT, COHORT, MENTION,
SCORE_PCT, TIMESTAMP. A third party with DASHBOARD_PROOF_SECRET can
recompute HMAC over the body up to the SIGNATURE line and confirm
authenticity.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import logging
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Flask, Response, render_template, request

from db import events_by_type, get_connection, list_students, per_student_stats

LOGGER = logging.getLogger(__name__)

AuthFn = Callable[[], "tuple[bool, Any]"]


def _mention_for(progress_pct: int, quiz_pct: int) -> str:
    """Auto-mention from progression + quiz average. See module docstring."""
    if progress_pct >= 80 and quiz_pct >= 70:
        return "tres_bien"
    if progress_pct >= 60 and quiz_pct >= 60:
        return "bien"
    if progress_pct >= 40:
        return "reussite"
    return "participation"


def _institution() -> str:
    """Issuing institution name. Configurable via env so a different
    school can re-brand without touching templates."""
    return os.environ.get("DASHBOARD_INSTITUTION", "M2 IA - Sorbonne Universite")


def sign_diploma(body: str, *, secret: bytes, student_token: str, cohort_id: str,
                 mention: str, score_pct: int) -> str:
    """Append the signed footer to a diploma body. Distinct SCHEME from
    proof_routes.sign_proof so a forged challenge proof cannot be
    repackaged as a diploma."""
    if not secret:
        raise RuntimeError("DASHBOARD_PROOF_SECRET missing or shorter than 16 chars")
    footer_lines = [
        "---",
        "DIPLOMA: HMAC-SHA256",
        "SCHEME: diploma.v1",
        "TIMESTAMP: " + datetime.now(timezone.utc).isoformat(),
        "STUDENT: " + student_token,
        "COHORT: " + cohort_id,
        "MENTION: " + mention,
        "SCORE_PCT: " + str(score_pct),
    ]
    signed_payload = body + "\n" + "\n".join(footer_lines) + "\n"
    sig = hmac.new(secret, signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return signed_payload + "SIGNATURE: " + sig + "\n"


def build_diploma_md(*, student_token: str, student_name: str, cohort_id: str,
                     mention: str, progress_pct: int, quiz_pct: int,
                     challenges_solved: int, hints_used: int,
                     hint_penalty: int, score_challenge: int,
                     flags_verified: int, quiz_submitted: bool,
                     journals_written: int, journal_words: int,
                     institution: str) -> str:
    """Markdown body up to (but not including) the SIGNATURE line.

    Same content drives both the ZIP batch (.md per student) and the
    HTML print page. Mirrors the structure of proof_routes.build_proof_markdown
    so a teacher can cross-check a diploma against the per-challenge proofs.
    """
    quiz_line = (
        "| Moyenne quiz | **" + str(quiz_pct) + "%** |"
        if quiz_submitted else
        "| Moyenne quiz | _aucun quiz soumis_ |"
    )
    retex_line = (
        "| Journaux retex rediges | **" + str(journals_written) + "** "
        "(" + str(journal_words) + " mots cumules) |"
        if journals_written > 0 else
        "| Journaux retex rediges | _aucun journal redige_ |"
    )
    lines = [
        "# Diplome - " + cohort_id,
        "",
        "Decerne par : **" + institution + "**",
        "",
        "## Recipiendaire",
        "",
        "| Champ | Valeur |",
        "|---|---|",
        "| Nom | " + (student_name or "_(non renseigne)_") + " |",
        "| Token UUID | `" + student_token + "` |",
        "| Cohorte | " + cohort_id + " |",
        "",
        "## Mention obtenue",
        "",
        "**" + mention.replace("_", " ").upper() + "**",
        "",
        "## Resultats consolides",
        "",
        "| Indicateur | Valeur |",
        "|---|---|",
        "| Progression challenges | **" + str(progress_pct) + "%** |",
        "| Challenges resolus | " + str(challenges_solved) + " |",
        "| Indices consommes | " + str(hints_used)
        + " (penalite cumulee " + str(hint_penalty) + "%) |",
        "| Score challenge (100 - penalite) | **" + str(score_challenge) + "/100** |",
        "| Flags CTF verifies | " + str(flags_verified) + " |",
        quiz_line,
        retex_line,
        "",
        "## Score final",
        "",
        "**Formule** : score_final = (score_challenge + score_quiz) / 2 + bonus_flag",
        "",
        "- score_challenge = " + str(score_challenge) + "/100 (apres deduction des indices)",
        "- score_quiz = " + (str(quiz_pct) + "/100" if quiz_submitted else "_non calculable, quiz non soumis_"),
        "- bonus_flag = +10 si flag CTF verifie (par challenge resolu)",
        "",
        "## Verification",
        "",
        "Ce diplome est tamper-evident : la signature HMAC-SHA256 ci-dessous "
        "couvre tout le corps du document. Toute alteration invalide la "
        "signature (verifier via `python dashboard/verify_proof.py`).",
        "",
    ]
    return "\n".join(lines)


def _gather_diploma_context(conn: Any, cohort_id: str, td_total: int = 13) -> dict[str, Any]:
    """Read students + per-student aggregated stats. Returns a dict
    keyed by student_token holding every input the diploma body and
    HTML page need : challenges_solved, hint penalty sum, real quiz
    average (from json_extract data.score), flags, journal entries
    written. Computes the final score and the mention from those.
    """
    students = list_students(conn, cohort_id)
    stats = per_student_stats(conn, cohort_id)
    stats_by_token = {r["student_token"]: r for r in stats}
    out: dict[str, dict[str, Any]] = {}
    for s in students:
        stat = stats_by_token.get(s["student_token"])
        if stat is not None:
            challenges_solved = int(stat["challenges_solved"] or 0)
            hints_used = int(stat["hints_used"] or 0)
            hint_penalty = int(stat["hint_penalty_sum"] or 0)
            quizzes_done = int(stat["quizzes_done"] or 0)
            quiz_avg_raw = stat["quiz_avg_score"]
            flags_verified = int(stat["flags_verified"] or 0)
            journals_written = int(stat["journals_written"] or 0)
            journal_words = int(stat["journal_word_total"] or 0)
        else:
            challenges_solved = hints_used = hint_penalty = quizzes_done = 0
            quiz_avg_raw = None
            flags_verified = journals_written = journal_words = 0

        progress_pct = min(100, round(100 * challenges_solved / td_total))
        # score_challenge = 100 - sum of hint cost_pct used (clamped to [0,100]).
        score_challenge = max(0, 100 - hint_penalty)
        # quiz_pct = real average of stored data.score values (per quiz
        # the event records "score" 0..100). None if no quiz submitted.
        quiz_pct = int(round(quiz_avg_raw)) if quiz_avg_raw is not None else 0
        # Mention uses progress_pct (broad coverage) AND quiz_pct (depth),
        # consistent with the per-challenge score formula in proof_routes
        # (avg of challenge + quiz + bonus_flag).
        out[s["student_token"]] = {
            "display_name": s["display_name"],
            "status": s["status"] if "status" in s.keys() else "validated",
            "challenges_solved": challenges_solved,
            "hints_used": hints_used,
            "hint_penalty": hint_penalty,
            "score_challenge": score_challenge,
            "flags_verified": flags_verified,
            "quizzes_done": quizzes_done,
            "quiz_pct": quiz_pct,
            "quiz_submitted": quiz_avg_raw is not None,
            "journals_written": journals_written,
            "journal_words": journal_words,
            "progress_pct": progress_pct,
            "mention": _mention_for(progress_pct, quiz_pct),
        }
    return out


def register_diploma_routes(
    app: Flask,
    auth_check_html: AuthFn,
    auth_check_json: AuthFn,
    *,
    proof_secret: Callable[[], bytes],
) -> None:

    @app.get("/admin/diploma/<token>")
    def diploma_html(token: str) -> Response:
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
        body = build_diploma_md(
            student_token=token,
            student_name=ctx["display_name"] or "",
            cohort_id=cohort_id,
            mention=ctx["mention"],
            progress_pct=ctx["progress_pct"],
            quiz_pct=ctx["quiz_pct"],
            challenges_solved=ctx["challenges_solved"],
            hints_used=ctx["hints_used"],
            hint_penalty=ctx["hint_penalty"],
            score_challenge=ctx["score_challenge"],
            flags_verified=ctx["flags_verified"],
            quiz_submitted=ctx["quiz_submitted"],
            journals_written=ctx["journals_written"],
            journal_words=ctx["journal_words"],
            institution=_institution(),
        )
        signed = sign_diploma(
            body, secret=proof_secret(),
            student_token=token, cohort_id=cohort_id,
            mention=ctx["mention"], score_pct=ctx["progress_pct"],
        )
        return Response(
            render_template(
                "diploma.html",
                cohort_id=cohort_id,
                student_token=token,
                student_name=ctx["display_name"] or "",
                mention=ctx["mention"],
                mention_label=ctx["mention"].replace("_", " ").upper(),
                progress_pct=ctx["progress_pct"],
                quiz_pct=ctx["quiz_pct"],
                quiz_submitted=ctx["quiz_submitted"],
                challenges_solved=ctx["challenges_solved"],
                hints_used=ctx["hints_used"],
                hint_penalty=ctx["hint_penalty"],
                score_challenge=ctx["score_challenge"],
                flags_verified=ctx["flags_verified"],
                journals_written=ctx["journals_written"],
                journal_words=ctx["journal_words"],
                institution=_institution(),
                signed_body=signed,
                issued_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ),
            content_type="text/html; charset=utf-8",
        )

    @app.get("/api/diplomas.zip")
    def diplomas_zip() -> Response:
        ok, err = auth_check_json()
        if not ok and err is not None:
            return err
        cohort_id = (request.args.get("cohort") or "").strip()
        if not cohort_id:
            return Response("missing cohort", status=400)
        include_all = request.args.get("include_all", "0").lower() in ("1", "true", "yes")
        if not proof_secret():
            return Response("diploma signing disabled", status=503)
        with get_connection() as conn:
            ctx_all = _gather_diploma_context(conn, cohort_id)
        if not ctx_all:
            return Response("no students in cohort", status=404)
        buf = io.BytesIO()
        written = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for token, ctx in ctx_all.items():
                # By default skip students who only qualify for the
                # "participation" mention (< 40% progression). The prof
                # can override via include_all=1.
                if not include_all and ctx["mention"] == "participation":
                    continue
                if ctx["status"] != "validated":
                    continue
                body = build_diploma_md(
                    student_token=token,
                    student_name=ctx["display_name"] or "",
                    cohort_id=cohort_id,
                    mention=ctx["mention"],
                    progress_pct=ctx["progress_pct"],
                    quiz_pct=ctx["quiz_pct"],
                    challenges_solved=ctx["challenges_solved"],
                    hints_used=ctx["hints_used"],
                    hint_penalty=ctx["hint_penalty"],
                    score_challenge=ctx["score_challenge"],
                    flags_verified=ctx["flags_verified"],
                    quiz_submitted=ctx["quiz_submitted"],
                    journals_written=ctx["journals_written"],
                    journal_words=ctx["journal_words"],
                    institution=_institution(),
                )
                signed = sign_diploma(
                    body, secret=proof_secret(),
                    student_token=token, cohort_id=cohort_id,
                    mention=ctx["mention"], score_pct=ctx["progress_pct"],
                )
                # Filename : <mention>_<sanitized_name_or_token>.md.
                safe = (ctx["display_name"] or token).replace("/", "_").replace(" ", "_")
                zf.writestr(f"{ctx['mention']}_{safe[:60]}.md", signed)
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
