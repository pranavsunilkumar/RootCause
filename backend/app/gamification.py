"""
Gamification, computed on the fly from existing Mastery/Attempt rows --
no separate "points" table to keep in sync, no risk of it drifting from
the real progress data.

Points:  +10 per mastered concept, +2 per passed attempt of any kind
          (rewards persistence, not just first-try luck).
Badges:  a handful of simple, explainable rules over the same data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .graph import ConceptGraph, graph as default_graph
from .models import Attempt, Mastery

POINTS_PER_MASTERED = 10
POINTS_PER_PASSED_ATTEMPT = 2


@dataclass
class Badge:
    code: str
    name: str
    description: str


@dataclass
class GamificationProfile:
    user_id: str
    points: int
    mastered_count: int
    passed_attempts: int
    current_streak: int
    badges: List[Badge]


def _current_streak(attempts_desc: List[Attempt]) -> int:
    """Consecutive passed attempts counting back from the most recent one."""
    streak = 0
    for a in attempts_desc:
        if a.passed:
            streak += 1
        else:
            break
    return streak


def compute_profile(db: Session, user_id: str, concept_graph: ConceptGraph = default_graph) -> GamificationProfile:
    mastered_count = db.execute(
        select(func.count()).select_from(Mastery).where(Mastery.user_id == user_id, Mastery.status == "mastered")
    ).scalar_one()

    attempts_desc = list(
        db.execute(select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.created_at.desc())).scalars()
    )
    passed_attempts = sum(1 for a in attempts_desc if a.passed)
    modes_used = {a.mode for a in attempts_desc}
    max_steps_upstream_diagnosed = _max_diagnosis_depth(attempts_desc, concept_graph)

    points = mastered_count * POINTS_PER_MASTERED + passed_attempts * POINTS_PER_PASSED_ATTEMPT
    streak = _current_streak(attempts_desc)

    badges: List[Badge] = []
    if mastered_count >= 1:
        badges.append(Badge("first_mastery", "First Mastery", "Mastered your first concept."))
    if mastered_count >= 5:
        badges.append(Badge("five_mastered", "Building Momentum", "Mastered 5 concepts."))
    if streak >= 3:
        badges.append(Badge("streak_3", "On a Roll", "3 passes in a row."))
    if "bughunt" in modes_used and any(a.mode == "bughunt" and a.passed for a in attempts_desc):
        badges.append(Badge("bug_hunter", "Bug Hunter", "Found a seeded misconception-bug."))
    if max_steps_upstream_diagnosed >= 2:
        badges.append(Badge("root_cause_finder", "Root Cause Finder", "Diagnosed a break 2+ concepts upstream."))
    if len(modes_used) >= 3:
        badges.append(Badge("well_rounded", "Well Rounded", "Used diagnose, bug hunt, and teach-back at least once each."))

    return GamificationProfile(
        user_id=user_id,
        points=points,
        mastered_count=mastered_count,
        passed_attempts=passed_attempts,
        current_streak=streak,
        badges=badges,
    )


def _max_diagnosis_depth(attempts_desc: List[Attempt], concept_graph: ConceptGraph) -> int:
    """
    Best-effort proxy for "diagnosed something N steps upstream": the
    longest prerequisite chain among concepts this user has ever failed
    a diagnose-mode check on (a real depth would need the original
    target concept, which isn't stored per-attempt in v1 -- this is an
    honest approximation, not exact telemetry).
    """
    best = 0
    for a in attempts_desc:
        if a.mode != "diagnose" or a.passed:
            continue
        try:
            chain_len = len(concept_graph.prereq_chain(a.concept_id)) - 1
        except KeyError:
            continue
        best = max(best, chain_len)
    return best


def leaderboard(db: Session, concept_graph: ConceptGraph = default_graph, limit: int = 20) -> List[GamificationProfile]:
    user_ids = [r[0] for r in db.execute(select(Attempt.user_id).distinct()).all()]
    profiles = [compute_profile(db, uid, concept_graph) for uid in user_ids]
    profiles.sort(key=lambda p: p.points, reverse=True)
    return profiles[:limit]
