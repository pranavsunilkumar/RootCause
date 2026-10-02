"""
The RootCause diagnosis engine.

This is the "concept-graph diagnosis" feature from the pitch deck: given
a concept the learner says they're stuck on, don't just re-explain it —
walk its prerequisite chain from the most foundational node upward and
find the first one the learner can't actually demonstrate. That node is
the diagnosis, however many steps upstream it sits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import os

from .grading import Grader, GradeResult, get_default_grader
from .graph import Concept, ConceptGraph, graph as default_graph


@dataclass
class ChainStep:
    concept_id: str
    name: str
    question: str


@dataclass
class NodeCheck:
    concept_id: str
    name: str
    result: GradeResult


@dataclass
class Diagnosis:
    target_concept: str
    broken_concept: Optional[str]  # None means every upstream node passed
    steps_upstream: int  # distance between the broken node and the target
    checked: List[NodeCheck]
    lesson_summary: str
    lesson_key_points: List[str]


class DiagnosisEngine:
    def __init__(self, concept_graph: ConceptGraph = default_graph, grader: Optional[Grader] = None):
        self.graph = concept_graph
        self.grader = grader or get_default_grader()

    def chain_for(self, concept_id: str) -> List[ChainStep]:
        """The ordered probe questions the frontend walks through, one at a time."""
        chain = self.graph.prereq_chain(concept_id)
        return [ChainStep(c.id, c.name, c.probe.question) for c in chain]

    def check_node(self, concept_id: str, answer: str) -> NodeCheck:
        """Grade a single node's probe answer. Stateless — the caller (the API
        layer, driven by the frontend) decides whether to keep walking."""
        node = self.graph.get(concept_id)
        result = self.grader.grade(answer, node.probe.keyword_groups)
        return NodeCheck(concept_id=node.id, name=node.name, result=result)

    def diagnose_from_checks(self, target_concept_id: str, checks: List[NodeCheck]) -> Diagnosis:
        """
        Given the checks performed so far (in chain order, stopping as soon
        as one fails), produce the final diagnosis. If every check passed,
        the "broken" concept is the target itself — the learner has all the
        prerequisites but still needs a direct explanation of the topic
        they originally asked about.
        """
        target = self.graph.get(target_concept_id)
        broken: Optional[NodeCheck] = next((c for c in checks if not c.result.passed), None)

        if broken is not None:
            node = self.graph.get(broken.concept_id)
            chain_ids = [s.concept_id for s in self.chain_for(target_concept_id)]
            steps_upstream = chain_ids.index(target.id) - chain_ids.index(node.id)
            return Diagnosis(
                target_concept=target.id,
                broken_concept=node.id,
                steps_upstream=steps_upstream,
                checked=checks,
                lesson_summary=node.summary,
                lesson_key_points=node.key_points,
            )

        return Diagnosis(
            target_concept=target.id,
            broken_concept=target.id,
            steps_upstream=0,
            checked=checks,
            lesson_summary=target.summary,
            lesson_key_points=target.key_points,
        )

    def ai_explain(self, diagnosis: "Diagnosis", learner_answer: str = "") -> Optional[str]:
        """
        AI-powered diagnosis: a short, personalized explanation of why the
        broken concept trips people up, referencing the learner's own
        (failing) answer where useful. Returns None when GEMINI_API_KEY
        isn't set or the call fails -- callers should fall back to
        `lesson_summary` / `lesson_key_points`, which are always present.
        """
        if not os.environ.get("GEMINI_API_KEY"):
            return None
        try:
            from google import genai

            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        except Exception:
            return None

        node = self.graph.get(diagnosis.broken_concept)
        target = self.graph.get(diagnosis.target_concept)
        prompt = (
            f"A learner trying to understand '{target.name}' turned out to actually be shaky on "
            f"'{node.name}', {diagnosis.steps_upstream} step(s) upstream. Key ideas of "
            f"'{node.name}': {'; '.join(node.key_points)}.\n"
            + (f"Their answer to a quick check on it was: {learner_answer!r}\n" if learner_answer else "")
            + "In 2-3 sentences, explain the likely gap in a warm, encouraging tone, and connect "
            f"it back to why it matters for '{target.name}'. No headers, no lists."
        )
        try:
            model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            resp = client.models.generate_content(model=model, contents=prompt)
            text = (resp.text or "").strip()
            return text or None
        except Exception:
            return None
