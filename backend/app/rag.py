"""
The generation half of RAG. Retrieves grounding context from the
concept graph via retrieval.py, then asks Gemini to answer using only
that context. Falls back to returning the retrieved summaries directly
(no LLM call) when GEMINI_API_KEY isn't set — same degrade-gracefully
pattern as grading.py, so this always returns something useful offline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from .retrieval import ConceptIndex, SearchHit, index as default_index


@dataclass
class RagAnswer:
    query: str
    answer: str
    sources: List[SearchHit]
    generated_by_llm: bool


class RagEngine:
    def __init__(self, concept_index: ConceptIndex = default_index, model: str | None = None):
        self.index = concept_index
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        try:
            from google import genai

            self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) if os.environ.get("GEMINI_API_KEY") else None
        except Exception:
            self._client = None

    def answer(self, query: str, top_k: int = 3) -> RagAnswer:
        hits = self.index.search(query, top_k=top_k)

        if not hits:
            return RagAnswer(query, "Nothing in the concept graph looks related to that yet.", [], False)

        if self._client is None:
            fallback = " ".join(f"{h.name}: {h.summary}" for h in hits)
            return RagAnswer(query, fallback, hits, False)

        context = "\n".join(f"- {h.name}: {h.summary}" for h in hits)
        prompt = (
            "Answer the learner's question in 2-3 sentences, using ONLY the concept "
            "context below. If the context doesn't fully cover the question, say what "
            "it does cover rather than inventing anything outside it.\n\n"
            f"Concept context:\n{context}\n\nLearner's question: {query}"
        )
        try:
            resp = self._client.models.generate_content(model=self.model, contents=prompt)
            text = (resp.text or "").strip()
            return RagAnswer(query, text or "No answer generated.", hits, True)
        except Exception:
            fallback = " ".join(f"{h.name}: {h.summary}" for h in hits)
            return RagAnswer(query, fallback, hits, False)


rag_engine = RagEngine()
