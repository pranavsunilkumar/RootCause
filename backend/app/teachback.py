"""
Teach-Back Grading: the learner explains a concept back in their own
words to a deliberately naive persona. We grade the explanation against
the concept's key points and, if something's missing, surface one of
that persona's "dumb" follow-up questions aimed at exactly the gap.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .grading import Grader, GradeResult, get_default_grader
from .graph import ConceptGraph, graph as default_graph

FOLLOWUPS_PATH = Path(__file__).parent / "data" / "followups.json"


@dataclass
class TeachBackResult:
    concept_id: str
    grade: GradeResult
    followup_question: Optional[str]


class TeachBackEngine:
    def __init__(self, concept_graph: ConceptGraph = default_graph, grader: Optional[Grader] = None):
        self.graph = concept_graph
        self.grader = grader or get_default_grader()
        self._followups = json.loads(FOLLOWUPS_PATH.read_text(encoding="utf-8"))

    def grade(self, concept_id: str, explanation: str) -> TeachBackResult:
        node = self.graph.get(concept_id)
        groups = [[point] + _loose_variants(point) for point in node.key_points]
        result = self.grader.grade(explanation, groups, labels=node.key_points)

        followup = None
        if result.missing:
            gap = result.missing[0]
            per_concept = self._followups.get(concept_id, {})
            followup = per_concept.get(gap) or self._generic_followup(gap)

        return TeachBackResult(concept_id=concept_id, grade=result, followup_question=followup)

    @staticmethod
    def _generic_followup(missing_point: str) -> str:
        return f"Wait, I don't get this part — can you explain: \u201c{missing_point}\u201d?"


def _loose_variants(point: str) -> List[str]:
    """Cheap extra keyword coverage so short paraphrases still match."""
    words = [w for w in point.lower().replace(",", " ").split() if len(w) > 4]
    return words[:4]
