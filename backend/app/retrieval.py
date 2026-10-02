"""
RAG-based concept retrieval — the retrieval half of RAG, implemented as
plain TF-IDF cosine similarity over each concept's summary + key points.
Deliberately dependency-free (stdlib `math`/`re`/`collections` only): no
vector database, no embeddings API, so it works identically offline and
in production with zero extra infra.

`rag.py` is the generation half: it calls `search()` here for grounding
context, then (optionally) asks Gemini to answer using only that
context, falling back to the raw retrieved summaries if no API key is
set — same graceful-degradation pattern as grading.py.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .graph import Concept, ConceptGraph, graph as default_graph

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "the", "is", "are", "of", "to", "and", "or", "in", "on", "for", "it", "this",
    "that", "with", "as", "by", "be", "its", "each", "one", "so", "then", "than", "into",
}


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _concept_text(c: Concept) -> str:
    return " ".join([c.name, c.summary, " ".join(c.key_points)])


@dataclass
class SearchHit:
    concept_id: str
    name: str
    score: float
    summary: str


class ConceptIndex:
    """Built once at import from the concept graph; O(n) to query, n=20-ish."""

    def __init__(self, concept_graph: ConceptGraph = default_graph):
        self.graph = concept_graph
        self._doc_tokens: Dict[str, List[str]] = {}
        self._doc_tf: Dict[str, Counter] = {}
        self._idf: Dict[str, float] = {}
        self._build()

    def _build(self) -> None:
        ids = self.graph.all_ids()
        for cid in ids:
            tokens = _tokenize(_concept_text(self.graph.get(cid)))
            self._doc_tokens[cid] = tokens
            self._doc_tf[cid] = Counter(tokens)

        n_docs = len(ids)
        df: Counter = Counter()
        for cid in ids:
            for term in set(self._doc_tokens[cid]):
                df[term] += 1
        # smoothed idf so an unseen-at-index-time term never divides by zero
        self._idf = {term: math.log((1 + n_docs) / (1 + count)) + 1 for term, count in df.items()}

    def _vector(self, tf: Counter) -> Dict[str, float]:
        total = sum(tf.values()) or 1
        return {term: (count / total) * self._idf.get(term, math.log(1 + len(self._doc_tokens)))
                for term, count in tf.items()}

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = 5) -> List[SearchHit]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        query_vec = self._vector(Counter(query_tokens))

        scored: List[Tuple[str, float]] = []
        for cid in self._doc_tokens:
            doc_vec = self._vector(self._doc_tf[cid])
            score = self._cosine(query_vec, doc_vec)
            if score > 0:
                scored.append((cid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        hits = []
        for cid, score in scored[:top_k]:
            node = self.graph.get(cid)
            hits.append(SearchHit(concept_id=cid, name=node.name, score=round(score, 4), summary=node.summary))
        return hits

    def related_to(self, concept_id: str, top_k: int = 3) -> List[SearchHit]:
        """Concepts textually similar to `concept_id`, excluding itself."""
        node = self.graph.get(concept_id)
        hits = self.search(_concept_text(node), top_k=top_k + 1)
        return [h for h in hits if h.concept_id != concept_id][:top_k]


index = ConceptIndex()
