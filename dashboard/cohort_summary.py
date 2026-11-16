"""Cohort summary builder for the JuiceLab teacher dashboard.

Holds build_cohort_summary(), the data payload behind the /dashboard HTML
view and the /api/cohort JSON endpoint. Moved out of app.py so the summary
can be built and tested against an isolated database without Flask and
without importing the app module. Reads the dashboard SQLite database
through the db helpers only; it never writes.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from db import get_connection, list_students, names_for_cohort, tags_for_cohort


def _duration_sec(first_ts: Any, last_ts: Any) -> int | None:
    """Int seconds between two ISO timestamps, or None when either cannot be
    parsed with datetime.fromisoformat. Naive datetimes are treated as UTC."""
    try:
        first = datetime.fromisoformat(first_ts)
        last = datetime.fromisoformat(last_ts)
    except (TypeError, ValueError):
        return None
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return int((last - first).total_seconds())


def build_cohort_summary(cohort_id: str) -> dict[str, Any]:
    """Read roster-bound events and return matrix cells and per-student totals.

    Purpose: build, for one cohort, the whole summary consumed by the teacher
    dashboard: the listed students, the touched challenges, the per-challenge
    matrix cells, per-student scores and per-challenge aggregate stats.

    Input: `cohort_id`, the identifier of the cohort to summarise. Requires an
    initialised dashboard database and a cohort identifier. The listed students
    are the roster students that have at least one event, plus every roster
    student whose status is 'validated' even without any event; students with
    status 'pending' or 'rejected' and no event are not listed.

    Returned keys:
      - "cohort_id": the requested cohort identifier.
      - "students": sorted list of listed student tokens.
      - "challenges": sorted list of challenge keys touched by listed students.
      - "matrix": per listed student token, a dict of per-challenge slots
        (empty dict for a student without any event). Each slot holds
        "hints", "journal", "quiz_score", "solved", "flag_verified",
        "last_ts" (raw client_ts of the student's last event on that
        challenge), "first_ts" (raw client_ts of the student's first event on
        that challenge) and "duration_sec" (see below).
      - "totals": per listed student token {"avg_score", "partial_score",
        "challenges_with_quiz", "challenges_touched"}. Final scores include
        only challenges with a submitted quiz; round ties to even, matching
        the per-challenge proof, before the existing verified-flag bonus.
        Partial scores remain separate.
      - "events_total": number of roster-bound event rows read.
      - "event_counts": per listed student token, total number of events of
        any type (0 for a student without event).
      - "names": token -> display label, for listed students that have one.
      - "tags": token -> tag status, for the tagged students of the cohort.
      - "active_students": number of listed students with at least one event.
      - "challenge_stats": per challenge key {"solved", "in_progress",
        "not_started", "avg_hints", "avg_duration_sec"}: how many listed
        students have a solved slot on it, have a slot without solving it, or
        have no slot on it (the three counters always add up to
        len(students)); the mean hint level over the students with a slot,
        rounded to 1 decimal; and the int(round(mean)) of the non-None slot
        durations, or None when none is computable. An empty cohort gives {}.

    "duration_sec" is the int number of seconds between the student's first
    and last event on the challenge (0 for a single event), or None when a
    timestamp of that slot cannot be parsed with datetime.fromisoformat; a
    naive datetime is treated as UTC.

    Limits: durations come from client timestamps, they measure the span
    between the first and the last recorded event on a challenge, not
    attention time. Reads data only; event truth and author identity are not
    established here.

    Database errors propagate to the caller.
    """
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
        # Validated roster students are listed even without any event so a
        # quiet but enrolled student still shows up as an empty matrix row.
        roster_rows = list_students(conn, cohort_id)
    validated_tokens = {
        str(r["student_token"]) for r in roster_rows if r["status"] == "validated"
    }

    students: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    challenge_keys: set[str] = set()
    # Total events per student, including session_start / connection events
    # that have no challenge_key. Used to surface activity in the matrix
    # row even before the student touches a real challenge.
    event_counts: dict[str, int] = defaultdict(int)

    # Validated students without events start with an empty matrix row; the
    # event loop below fills (or creates) the rows of students that emitted.
    for token in validated_tokens:
        _ = students[token]

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
                    "first_ts": row["client_ts"],
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
                # Match the proof generator: nearest integer, ties to even (Python round).
                sums.append(min(100, round((score_chall + quiz) / 2) + bonus)); chall_done += 1
            else:
                partials.append(score_chall)
        avg = round(sum(sums) / len(sums)) if sums else None
        partial = round(sum(partials) / len(partials)) if partials else None
        totals[student] = {"avg_score": avg, "partial_score": partial,
            "challenges_with_quiz": chall_done, "challenges_touched": len(per_chall)}

    # Per-slot time span: seconds between the student's first and last
    # recorded event on the challenge, from the raw client timestamps.
    for per_chall in students.values():
        for slot in per_chall.values():
            slot["duration_sec"] = _duration_sec(slot["first_ts"], slot["last_ts"])

    # One stats line per challenge, over the listed students.
    challenge_stats: dict[str, dict[str, Any]] = {}
    for challenge in sorted_challenges:
        solved = 0
        in_progress = 0
        not_started = 0
        hint_levels: list[int] = []
        durations: list[int] = []
        for student in sorted_students:
            slot = students[student].get(challenge)
            if slot is None:
                not_started += 1
                continue
            hint_levels.append(int(slot["hints"]))
            if slot["duration_sec"] is not None:
                durations.append(int(slot["duration_sec"]))
            if slot["solved"]:
                solved += 1
            else:
                in_progress += 1
        challenge_stats[challenge] = {
            "solved": solved,
            "in_progress": in_progress,
            "not_started": not_started,
            "avg_hints": round(sum(hint_levels) / len(hint_levels), 1),
            "avg_duration_sec": (
                int(round(sum(durations) / len(durations))) if durations else None
            ),
        }

    active_students = sum(1 for s in sorted_students if event_counts.get(s, 0) > 0)

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
        "active_students": active_students,
        "challenge_stats": challenge_stats,
    }
