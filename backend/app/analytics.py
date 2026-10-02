"""
Analytics dashboard data. Everything here is a straightforward
aggregate SQL query over Attempt/Mastery -- no separate analytics
pipeline, no batch jobs, nothing that can drift out of sync with the
live data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .graph import ConceptGraph, graph as default_graph
from .models import Attempt, Mastery


@dataclass
class ConceptStat:
    concept_id: str
    name: str
    attempts: int
    passes: int
    pass_rate: float


@dataclass
class ModeStat:
    mode: str
    attempts: int
    passes: int
    pass_rate: float


@dataclass
class AnalyticsOverview:
    active_learners: int
    total_attempts: int
    overall_pass_rate: float
    total_mastered: int
    by_mode: List[ModeStat]
    hardest_concepts: List[ConceptStat]  # lowest pass rate first, min 2 attempts
    most_practiced_concepts: List[ConceptStat]


def _pass_rate(passes: int, attempts: int) -> float:
    return round(passes / attempts, 3) if attempts else 0.0


def compute_overview(db: Session, concept_graph: ConceptGraph = default_graph, min_attempts_for_hardest: int = 2) -> AnalyticsOverview:
    total_attempts = db.execute(select(func.count()).select_from(Attempt)).scalar_one()
    total_passes = db.execute(select(func.count()).select_from(Attempt).where(Attempt.passed.is_(True))).scalar_one()
    active_learners = db.execute(select(func.count(func.distinct(Attempt.user_id)))).scalar_one()
    total_mastered = db.execute(select(func.count()).select_from(Mastery).where(Mastery.status == "mastered")).scalar_one()

    modes = [r[0] for r in db.execute(select(Attempt.mode).distinct()).all()]
    by_mode: List[ModeStat] = []
    for mode in modes:
        attempts = db.execute(select(func.count()).select_from(Attempt).where(Attempt.mode == mode)).scalar_one()
        passes = db.execute(
            select(func.count()).select_from(Attempt).where(Attempt.mode == mode, Attempt.passed.is_(True))
        ).scalar_one()
        by_mode.append(ModeStat(mode=mode, attempts=attempts, passes=passes, pass_rate=_pass_rate(passes, attempts)))
    by_mode.sort(key=lambda m: m.attempts, reverse=True)

    concept_ids = [r[0] for r in db.execute(select(Attempt.concept_id).distinct()).all()]
    concept_stats: List[ConceptStat] = []
    for cid in concept_ids:
        attempts = db.execute(select(func.count()).select_from(Attempt).where(Attempt.concept_id == cid)).scalar_one()
        passes = db.execute(
            select(func.count()).select_from(Attempt).where(Attempt.concept_id == cid, Attempt.passed.is_(True))
        ).scalar_one()
        try:
            name = concept_graph.get(cid).name
        except KeyError:
            name = cid
        concept_stats.append(ConceptStat(concept_id=cid, name=name, attempts=attempts, passes=passes, pass_rate=_pass_rate(passes, attempts)))

    hardest = sorted(
        [c for c in concept_stats if c.attempts >= min_attempts_for_hardest],
        key=lambda c: c.pass_rate,
    )[:5]
    most_practiced = sorted(concept_stats, key=lambda c: c.attempts, reverse=True)[:5]

    return AnalyticsOverview(
        active_learners=active_learners,
        total_attempts=total_attempts,
        overall_pass_rate=_pass_rate(total_passes, total_attempts),
        total_mastered=total_mastered,
        by_mode=by_mode,
        hardest_concepts=hardest,
        most_practiced_concepts=most_practiced,
    )
