"""Readable learning history built from the raw event log.

Three views share the same parsing rules :

* ``challenge_stories`` : one story per challenge for one student (start,
  hints, quiz, journal, resolution, duration), consumed by the student
  detail page instead of the raw event table.
* ``split_sessions`` : cuts a cohort event log into teaching sessions (TDs).
  A new session starts when the cohort was silent for longer than the
  monitor session horizon (``monitor.session_min``, default 240 minutes).
* ``student_sessions`` : progression of one student from one session to
  the next, aligned on the cohort sessions.

Timestamps : the server timestamp decides session membership (one clock for
the whole cohort) ; stories show the client timestamp when present, as the
rest of the dashboard does. Unparseable timestamps never raise : the event
is kept, only the durations that depend on it become ``None``.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

import monitor


def session_gap_minutes() -> int:
    """Silence (minutes) that separates two sessions : monitor.session_min."""
    return monitor._seuils()["session_min"]


def parse_ts(value: Any) -> datetime | None:
    """ISO-8601 string -> aware UTC datetime, or None when unparseable.
    A naive timestamp is read as UTC."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _data(ev: Mapping[str, Any]) -> dict:
    raw = ev["data_json"] if "data_json" in ev.keys() else None
    try:
        data = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _shown_ts(ev: Mapping[str, Any]) -> str | None:
    return ev["client_ts"] or ev["server_ts"]


def _seconds(start: str | None, end: str | None) -> int | None:
    a, b = parse_ts(start), parse_ts(end)
    if a is None or b is None:
        return None
    return max(0, int((b - a).total_seconds()))


def challenge_stories(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One story per challenge, in the order the student started them.

    Input : event rows (``event_type``, ``challenge_key``, ``data_json``,
    ``client_ts``, ``server_ts``) of ONE student, any order of insertion.
    Events without challenge key (session_start, badge_earned...) are left
    out : they belong to no challenge.

    Each story : ``challenge_key``, ``status`` ("solved" | "in_progress"),
    ``started_at``, ``last_at``, ``solved_at``, ``duration_sec`` (start to
    resolution, or start to last event when unsolved ; None when a timestamp
    is unparseable), ``hints`` [{level, cost_pct, ts}], ``hint_cost_total``,
    ``quiz`` {score, ts} or None, ``journal_words`` (after-phase journal,
    0 when absent), ``flag_verified`` and ``steps`` : the ordered list
    {ts, kind, ...} the page turns into sentences, kind in
    start | hint | solved | flag | quiz | journal.
    """
    stories: dict[str, dict[str, Any]] = {}
    for ev in events:
        key = ev["challenge_key"]
        if not key:
            continue
        ts = _shown_ts(ev)
        st = stories.get(key)
        if st is None:
            st = stories[key] = {
                "challenge_key": key, "status": "in_progress",
                "started_at": ts, "last_at": ts, "solved_at": None,
                "duration_sec": None, "hints": [], "hint_cost_total": 0,
                "quiz": None, "journal_words": 0, "flag_verified": False,
                "steps": [{"ts": ts, "kind": "start"}],
            }
        st["last_at"] = ts
        data = _data(ev)
        et = ev["event_type"]
        if et == "hint_revealed":
            cost = data.get("cost_pct")
            cost = int(cost) if isinstance(cost, (int, float)) else 0
            st["hints"].append({"level": data.get("level"), "cost_pct": cost, "ts": ts})
            st["hint_cost_total"] += cost
            st["steps"].append({"ts": ts, "kind": "hint", "level": data.get("level"), "cost_pct": cost})
        elif et == "challenge_solved" and st["solved_at"] is None:
            st["status"] = "solved"
            st["solved_at"] = ts
            st["steps"].append({"ts": ts, "kind": "solved"})
        elif et == "flag_verified" and not st["flag_verified"]:
            st["flag_verified"] = True
            st["steps"].append({"ts": ts, "kind": "flag"})
        elif et == "quiz_completed":
            score = data.get("score")
            score = int(score) if isinstance(score, (int, float)) else None
            st["quiz"] = {"score": score, "ts": ts}
            st["steps"].append({"ts": ts, "kind": "quiz", "score": score})
        elif et == "journal_filled" and data.get("phase") == "after":
            words = data.get("word_count")
            st["journal_words"] = int(words) if isinstance(words, (int, float)) else 0
            st["steps"].append({"ts": ts, "kind": "journal", "words": st["journal_words"]})
    for st in stories.values():
        st["duration_sec"] = _seconds(st["started_at"], st["solved_at"] or st["last_at"])
    return list(stories.values())


def split_sessions(events: Iterable[Mapping[str, Any]],
                   gap_minutes: int | None = None) -> list[dict[str, Any]]:
    """Cut a cohort event log into sessions, oldest first.

    A session is a run of events (ordered by server timestamp) where no two
    consecutive events are more than ``gap_minutes`` apart (default
    ``session_gap_minutes()``). Events whose server timestamp cannot be
    parsed are ignored here. Each session : ``index`` (1-based), ``start``,
    ``end`` (ISO, UTC), ``events`` (count), ``students`` (sorted tokens).
    """
    gap = timedelta(minutes=gap_minutes if gap_minutes is not None else session_gap_minutes())
    stamped = sorted(
        (dt, ev["student_token"]) for ev in events
        if (dt := parse_ts(ev["server_ts"])) is not None
    )
    sessions: list[dict[str, Any]] = []
    for dt, token in stamped:
        cur = sessions[-1] if sessions else None
        if cur is None or dt - cur["_end"] > gap:
            cur = {"_start": dt, "_end": dt, "events": 0, "_students": set()}
            sessions.append(cur)
        cur["_end"] = dt
        cur["events"] += 1
        cur["_students"].add(token)
    return [{
        "index": i + 1,
        "start": s["_start"].isoformat(),
        "end": s["_end"].isoformat(),
        "events": s["events"],
        "students": sorted(s["_students"]),
    } for i, s in enumerate(sessions)]


def in_session(ev: Mapping[str, Any], session: Mapping[str, Any]) -> bool:
    """True when the event's server timestamp falls inside ``session``."""
    dt = parse_ts(ev["server_ts"])
    return dt is not None and parse_ts(session["start"]) <= dt <= parse_ts(session["end"])


def student_sessions(student_events: list[Mapping[str, Any]],
                     sessions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Progression of one student across the cohort ``sessions``.

    One entry per cohort session (attended or not, so a missed TD shows) :
    ``index``, ``start``, ``attended`` (bool), ``events``, ``solved_new``
    (challenges solved for the first time in that session, sorted),
    ``solved_total`` (cumulative distinct solves at the end of the
    session), ``hints``, ``quiz_avg`` (None without quiz).
    """
    solved_before: set[str] = set()
    out: list[dict[str, Any]] = []
    for s in sessions:
        evs = [e for e in student_events if in_session(e, s)]
        new: set[str] = set()
        hints = 0
        scores: list[int] = []
        for e in evs:
            et = e["event_type"]
            if et == "challenge_solved" and e["challenge_key"] and e["challenge_key"] not in solved_before:
                new.add(e["challenge_key"])
            elif et == "hint_revealed":
                hints += 1
            elif et == "quiz_completed":
                score = _data(e).get("score")
                if isinstance(score, (int, float)):
                    scores.append(int(score))
        solved_before |= new
        out.append({
            "index": s["index"], "start": s["start"], "attended": bool(evs),
            "events": len(evs), "solved_new": sorted(new),
            "solved_total": len(solved_before), "hints": hints,
            "quiz_avg": round(sum(scores) / len(scores)) if scores else None,
        })
    return out
