"""
RootCause concept graph.

Loads the hand-curated AI/ML dependency DAG from data/concepts.json and
exposes the one operation the whole diagnosis engine is built on:
`prereq_chain(concept_id)` -> the concept's prerequisites in dependency
order (most foundational first), ending with the concept itself.

Walking that chain from the front is exactly the "diagnose upstream,
don't re-explain the topic you were asked about" idea from the pitch:
the first node in the chain the learner fails on IS the root cause.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

DATA_PATH = Path(__file__).parent / "data" / "concepts.json"


@dataclass
class ProbeSpec:
    question: str
    keyword_groups: List[List[str]] = field(default_factory=list)


@dataclass
class Concept:
    id: str
    name: str
    prereqs: List[str]
    aliases: List[str]
    summary: str
    key_points: List[str]
    probe: ProbeSpec


class ConceptGraph:
    """In-memory representation of the concept DAG, loaded once at startup."""

    def __init__(self, path: Path = DATA_PATH):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._nodes: Dict[str, Concept] = {}
        for item in raw:
            probe_raw = item["probe"]
            self._nodes[item["id"]] = Concept(
                id=item["id"],
                name=item["name"],
                prereqs=list(item.get("prereqs", [])),
                aliases=list(item.get("aliases", [])),
                summary=item["summary"],
                key_points=list(item["key_points"]),
                probe=ProbeSpec(question=probe_raw["q"], keyword_groups=probe_raw["keywords"]),
            )
        self._validate()

    def _validate(self) -> None:
        for node in self._nodes.values():
            for p in node.prereqs:
                if p not in self._nodes:
                    raise ValueError(f"{node.id} lists unknown prereq {p!r}")
        # cycle check (Kahn's algorithm)
        indegree = {nid: 0 for nid in self._nodes}
        for node in self._nodes.values():
            for p in node.prereqs:
                indegree[node.id] += 1
        queue = [nid for nid, d in indegree.items() if d == 0]
        seen = 0
        children: Dict[str, List[str]] = {nid: [] for nid in self._nodes}
        for node in self._nodes.values():
            for p in node.prereqs:
                children[p].append(node.id)
        while queue:
            nid = queue.pop()
            seen += 1
            for child in children[nid]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if seen != len(self._nodes):
            raise ValueError("concept graph has a cycle")

    def __len__(self) -> int:
        return len(self._nodes)

    def all_ids(self) -> List[str]:
        return list(self._nodes.keys())

    def get(self, concept_id: str) -> Concept:
        if concept_id not in self._nodes:
            raise KeyError(f"unknown concept id: {concept_id!r}")
        return self._nodes[concept_id]

    def resolve(self, text: str) -> str | None:
        """Best-effort match of free text (an id, name, or alias) to a concept id."""
        needle = text.strip().lower()
        for node in self._nodes.values():
            if needle == node.id.lower() or needle == node.name.lower():
                return node.id
            if needle in (a.lower() for a in node.aliases):
                return node.id
        # loose substring fallback
        for node in self._nodes.values():
            if needle in node.name.lower() or node.name.lower() in needle:
                return node.id
        return None

    def topo_order(self) -> List[str]:
        """
        Every concept id, in a valid topological order (each id appears
        after all of its own prerequisites). Stable: ties are broken by
        insertion order in concepts.json, so this is deterministic across
        runs. Used by the path engine to pick "the earliest unresolved
        node" without recomputing order per request.
        """
        indegree = {nid: len(n.prereqs) for nid, n in self._nodes.items()}
        children: Dict[str, List[str]] = {nid: [] for nid in self._nodes}
        for node in self._nodes.values():
            for p in node.prereqs:
                children[p].append(node.id)

        ready = [nid for nid in self._nodes if indegree[nid] == 0]
        ordered: List[str] = []
        while ready:
            nid = ready.pop(0)
            ordered.append(nid)
            for child in children[nid]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        return ordered

    def prereq_chain(self, concept_id: str) -> List[Concept]:
        """
        Depth-first post-order traversal of the transitive prerequisite
        closure of `concept_id`, deduplicated, so every concept appears
        strictly after all of its own prerequisites and the target
        concept is always last. This is the order RootCause quizzes a
        learner in: most foundational node first.
        """
        target = self.get(concept_id)
        visited: set[str] = set()
        ordered: List[Concept] = []

        def visit(node: Concept) -> None:
            if node.id in visited:
                return
            visited.add(node.id)
            for p in node.prereqs:
                visit(self.get(p))
            ordered.append(node)

        visit(target)
        return ordered

    def to_public_list(self) -> List[dict]:
        return [
            {
                "id": n.id,
                "name": n.name,
                "prereqs": n.prereqs,
                "summary": n.summary,
            }
            for n in self._nodes.values()
        ]


# module-level singleton, imported by the API layer
graph = ConceptGraph()
