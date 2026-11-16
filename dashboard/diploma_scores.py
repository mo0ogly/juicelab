"""Diploma figures computed per challenge, then averaged.

The per-challenge rule is the one printed on every challenge proof
(proof_routes.build_proof_markdown) :

    score_challenge = max(0, 100 - sum of the hint costs on THAT challenge)
    score_final     = min(100, round((score_challenge + score_quiz) / 2) + bonus_flag)
    bonus_flag      = 10 when the CTF flag of the challenge was verified

The diploma only counts SOLVED challenges and averages them. A solved
challenge without quiz counts its quiz as 0 in the final score ; the
diploma states how many solved challenges had no quiz, so the teacher sees
why a score is low. Hints taken on unsolved challenges cost nothing on the
diploma (they are still reported in ``hints_used``).

The mention keeps the historical thresholds (operator policy, unchanged by
this module) applied to (progression, final score) instead of
(progression, raw quiz average).
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

FLAG_BONUS = 10  # same bonus as proof_routes and the overlay scoring service


def mention_for(progress_pct: int, final_score: int | None) -> str:
    """Mention from progression (% of parcours challenges solved) and final
    score (None = nothing solved, treated as 0).

    tres_bien : progression >= 80 and final >= 70
    bien      : progression >= 60 and final >= 60
    reussite  : progression >= 40
    participation otherwise.
    """
    final = final_score or 0
    if progress_pct >= 80 and final >= 70:
        return "tres_bien"
    if progress_pct >= 60 and final >= 60:
        return "bien"
    if progress_pct >= 40:
        return "reussite"
    return "participation"


def _mean(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None


def challenge_score(story: Mapping[str, Any]) -> dict[str, Any]:
    """Scores of one solved challenge story (learning_story.challenge_stories)."""
    challenge = max(0, 100 - int(story["hint_cost_total"]))
    quiz = story["quiz"]["score"] if story.get("quiz") else None
    bonus = FLAG_BONUS if story["flag_verified"] else 0
    return {
        "challenge_key": story["challenge_key"],
        "score_challenge": challenge,
        "score_quiz": quiz,
        "bonus_flag": bonus,
        "score_final": min(100, round((challenge + (quiz or 0)) / 2) + bonus),
    }


def diploma_figures(stories: Iterable[Mapping[str, Any]], td_total: int) -> dict[str, Any]:
    """Every figure the diploma prints, from one student's challenge stories.

    Returns : ``challenges_solved``, ``progress_pct`` (solved / td_total,
    capped at 100), ``score_challenge`` / ``quiz_pct`` / ``final_score``
    (averages over solved challenges ; None when no solved challenge, or
    for ``quiz_pct`` when no solved challenge has a quiz), ``quiz_missing``
    (solved challenges without quiz), ``flags_verified``, ``hints_used`` and
    ``hint_penalty`` (all challenges, informative), ``per_challenge`` and
    ``mention``.
    """
    stories = list(stories)
    solved = [challenge_score(s) for s in stories if s["status"] == "solved"]
    quizzes = [c["score_quiz"] for c in solved if c["score_quiz"] is not None]
    progress = min(100, round(100 * len(solved) / td_total)) if td_total > 0 else 0
    final = _mean([c["score_final"] for c in solved])
    return {
        "challenges_solved": len(solved),
        "progress_pct": progress,
        "score_challenge": _mean([c["score_challenge"] for c in solved]),
        "quiz_pct": _mean(quizzes),
        "quiz_missing": len(solved) - len(quizzes),
        "final_score": final,
        "flags_verified": sum(1 for s in stories if s["flag_verified"]),
        "hints_used": sum(len(s["hints"]) for s in stories),
        "hint_penalty": sum(int(s["hint_cost_total"]) for s in stories),
        "per_challenge": solved,
        "mention": mention_for(progress, final),
    }
