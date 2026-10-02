"""
Learning recommendations. Broader than path.py's single "what's next":
- a ranked shortlist (not just the top pick) of weak/unlocked concepts
- for each weak concept, textually related concepts from retrieval.py
  that aren't necessarily direct prerequisites -- catches lateral gaps
  the pure dependency graph wouldn't (e.g. two attention-adjacent ideas
  that don't formally depend on each other but commonly confuse people
  together).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .graph import ConceptGraph, graph as default_graph
from .retrieval import ConceptIndex, SearchHit, index as default_index
from .store import STATUS_MASTERED, STATUS_UNSEEN, STATUS_WEAK, ProgressStore, store as default_store


@dataclass
class RecommendedConcept:
    concept_id: str
    name: str
    status: str
    reason: str
    related: List[SearchHit]


class RecommendationEngine:
    def __init__(
        self,
        concept_graph: ConceptGraph = default_graph,
        concept_index: ConceptIndex = default_index,
        progress_store: ProgressStore = default_store,
    ):
        self.graph = concept_graph
        self.index = concept_index
        self.store = progress_store
        self._order = concept_graph.topo_order()

    def recommend(self, user_id: str, limit: int = 5) -> List[RecommendedConcept]:
        mastery = self.store.mastery_map(user_id, self.graph.all_ids())
        status: Dict[str, str] = {cid: e.status for cid, e in mastery.items()}

        picks: List[RecommendedConcept] = []

        # weak concepts first, most foundational first
        for cid in self._order:
            if status[cid] != STATUS_WEAK:
                continue
            picks.append(
                RecommendedConcept(
                    concept_id=cid,
                    name=self.graph.get(cid).name,
                    status=STATUS_WEAK,
                    reason="You're currently weak here.",
                    related=self.index.related_to(cid, top_k=2),
                )
            )

        # then unlocked-but-unseen concepts (prereqs mastered)
        for cid in self._order:
            if len(picks) >= limit:
                break
            if status[cid] != STATUS_UNSEEN:
                continue
            node = self.graph.get(cid)
            if all(status[p] == STATUS_MASTERED for p in node.prereqs):
                picks.append(
                    RecommendedConcept(
                        concept_id=cid,
                        name=node.name,
                        status=STATUS_UNSEEN,
                        reason="Ready for you: every prerequisite is mastered." if node.prereqs else "A good starting point.",
                        related=self.index.related_to(cid, top_k=2),
                    )
                )

        return picks[:limit]


recommendation_engine = RecommendationEngine()
