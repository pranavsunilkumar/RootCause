"""
Personalized Path: the feature from the pitch deck that "auto-sequences
the next lesson based on which graph nodes are still weak."

The policy is deliberately simple and explainable — a judge (or a
learner) should be able to guess the recommendation before seeing it:

  1. If the learner has any WEAK concepts (failed a diagnosis, bug hunt,
     or teach-back on it), recommend the most foundational one — fixing
     it is most likely to unblock several other weak/unseen concepts
     downstream, which is the whole thesis of RootCause.
  2. Otherwise, recommend the most foundational UNSEEN concept whose
     prerequisites are all already mastered — i.e. the next node on the
     frontier of the graph the learner is actually ready for.
  3. If no unseen concept has all its prerequisites mastered yet (new
     learner, nothing mastered), fall back to the most foundational
     unseen concept overall — always a true root (no prereqs).
  4. If every concept is mastered, there's nothing left to recommend.

"Most foundational" = earliest in the graph's global topological order,
computed once in graph.py and reused here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .graph import ConceptGraph, graph as default_graph
from .store import STATUS_MASTERED, STATUS_UNSEEN, STATUS_WEAK, ProgressStore, store as default_store

REASON_WEAKEST_LINK = "weakest_link"
REASON_NEXT_UNLOCKED = "next_unlocked"
REASON_NEXT_ROOT = "next_root"
REASON_ALL_MASTERED = "all_mastered"

_REASON_TEXT = {
    REASON_WEAKEST_LINK: "This is the most foundational concept you're currently weak on — fixing it is likely to unblock several others.",
    REASON_NEXT_UNLOCKED: "You've mastered everything this concept needs — it's the next one you're ready for.",
    REASON_NEXT_ROOT: "A good starting point: it has no prerequisites of its own.",
    REASON_ALL_MASTERED: "Every concept in the graph is mastered. Nothing queued up.",
}


@dataclass
class NextStep:
    concept_id: Optional[str]
    reason_code: str
    reason: str


class PathEngine:
    def __init__(self, concept_graph: ConceptGraph = default_graph, progress_store: ProgressStore = default_store):
        self.graph = concept_graph
        self.store = progress_store
        self._order = concept_graph.topo_order()

    def next_concept(self, user_id: str) -> NextStep:
        mastery = self.store.mastery_map(user_id, self.graph.all_ids())
        status: Dict[str, str] = {cid: entry.status for cid, entry in mastery.items()}

        weak_in_order = [cid for cid in self._order if status[cid] == STATUS_WEAK]
        if weak_in_order:
            return self._step(weak_in_order[0], REASON_WEAKEST_LINK)

        for cid in self._order:
            if status[cid] != STATUS_UNSEEN:
                continue
            prereqs = self.graph.get(cid).prereqs
            if all(status[p] == STATUS_MASTERED for p in prereqs):
                reason_code = REASON_NEXT_ROOT if not prereqs else REASON_NEXT_UNLOCKED
                return self._step(cid, reason_code)

        unseen_in_order = [cid for cid in self._order if status[cid] == STATUS_UNSEEN]
        if unseen_in_order:
            return self._step(unseen_in_order[0], REASON_NEXT_ROOT)

        return NextStep(concept_id=None, reason_code=REASON_ALL_MASTERED, reason=_REASON_TEXT[REASON_ALL_MASTERED])

    def _step(self, concept_id: str, reason_code: str) -> NextStep:
        return NextStep(concept_id=concept_id, reason_code=reason_code, reason=_REASON_TEXT[reason_code])

    def full_order(self) -> List[str]:
        return list(self._order)


path_engine = PathEngine()
