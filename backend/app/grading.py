"""
Grading backends for RootCause.

Every place that needs to judge free-text (a probe answer, a teach-back
explanation) goes through the `Grader` interface below. There are two
implementations:

- KeywordGrader: zero-dependency, deterministic, offline. Each concept
  in concepts.json ships a list of "keyword groups" — a group is a set
  of synonyms for one idea that answer must contain. The score is the
  fraction of groups the answer hits. This is what runs out of the box
  and what the unit tests exercise directly.

- GeminiGrader: same interface, backed by the Google Gemini API for a
  richer, more forgiving read of the learner's wording. Used automatically
  when GEMINI_API_KEY is set; falls back to KeywordGrader on any error so
  a flaky/missing network never breaks the demo.

Both return a GradeResult so the rest of the app never has to care
which one actually ran.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import List, Protocol


@dataclass
class GradeResult:
    score: float  # 0..1
    passed: bool
    matched: List[str]  # human-readable ideas the answer covered
    missing: List[str]  # human-readable ideas the answer did not cover
    feedback: str


PASS_THRESHOLD = 0.6
_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    return " " + " ".join(_WORD_RE.findall(text.lower())) + " "


class Grader(Protocol):
    def grade(self, answer: str, keyword_groups: List[List[str]], labels: List[str] | None = None) -> GradeResult: ...


class KeywordGrader:
    """Deterministic, offline. No network, no API key required."""

    def grade(self, answer: str, keyword_groups: List[List[str]], labels: List[str] | None = None) -> GradeResult:
        if not keyword_groups:
            return GradeResult(1.0, True, [], [], "No specific check for this prompt — marked complete.")

        haystack = _normalize(answer or "")
        matched_idx: List[int] = []
        for i, group in enumerate(keyword_groups):
            for kw in group:
                needle = kw.lower()
                # phrase or single token match against normalized haystack
                if " " in needle or "'" in needle:
                    if needle in (answer or "").lower():
                        matched_idx.append(i)
                        break
                elif f" {needle} " in haystack:
                    matched_idx.append(i)
                    break

        score = len(matched_idx) / len(keyword_groups)
        passed = score >= PASS_THRESHOLD
        labels = labels or [f"idea {i + 1}" for i in range(len(keyword_groups))]
        matched = [labels[i] for i in matched_idx]
        missing = [labels[i] for i in range(len(keyword_groups)) if i not in matched_idx]

        if not (answer or "").strip():
            feedback = "No answer given."
        elif passed and not missing:
            feedback = "Covers everything the check was looking for."
        elif passed:
            feedback = "Good enough to move on, though it didn't mention: " + ", ".join(missing) + "."
        else:
            feedback = "Missing the key idea(s): " + ", ".join(missing) + "."

        return GradeResult(round(score, 2), passed, matched, missing, feedback)


class GeminiGrader:
    """
    Optional richer grader. Same contract as KeywordGrader, but asks
    Gemini to judge the explanation and returns which of the target
    ideas it actually covered, in the learner's own words. Falls back
    to KeywordGrader transparently if the API call fails for any
    reason (no key, no network, bad response) so callers never see the
    difference except in quality of feedback.
    """

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self._fallback = KeywordGrader()
        try:
            from google import genai  # imported lazily so KeywordGrader-only installs don't need it

            self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        except Exception:
            self._client = None

    def grade(self, answer: str, keyword_groups: List[List[str]], labels: List[str] | None = None) -> GradeResult:
        if self._client is None or not (answer or "").strip():
            return self._fallback.grade(answer, keyword_groups, labels)

        labels = labels or [f"idea {i + 1}" for i in range(len(keyword_groups))]
        ideas = "\n".join(f"{i + 1}. {label}" for i, label in enumerate(labels))
        prompt = (
            "You are grading a learner's free-text explanation against a short list of "
            "required ideas. Be generous about phrasing — judge whether the IDEA is present, "
            "not whether the wording matches.\n\n"
            f"Required ideas:\n{ideas}\n\n"
            f"Learner's answer:\n{answer}\n\n"
            "Respond with ONLY a JSON object, no prose, no markdown fences, in this exact "
            'shape: {"covered_idea_numbers": [1, 3], "feedback": "one short encouraging sentence"}'
        )
        try:
            resp = self._client.models.generate_content(model=self.model, contents=prompt)
            text = (resp.text or "").strip()
            data = json.loads(text.strip("`"))
            covered = {int(n) for n in data.get("covered_idea_numbers", [])}
            matched = [labels[i] for i in range(len(labels)) if (i + 1) in covered]
            missing = [labels[i] for i in range(len(labels)) if (i + 1) not in covered]
            score = len(matched) / len(labels) if labels else 1.0
            passed = score >= PASS_THRESHOLD
            feedback = data.get("feedback") or ("Nice, that covers it." if passed else "Missing something important.")
            return GradeResult(round(score, 2), passed, matched, missing, feedback)
        except Exception:
            # Never let a flaky API call break the tutoring loop.
            return self._fallback.grade(answer, keyword_groups, labels)


def get_default_grader() -> Grader:
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiGrader()
    return KeywordGrader()
