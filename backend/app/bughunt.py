"""
Bug Hunt Challenges: a runnable snippet seeded with exactly one
misconception-bug. Finding the right line is itself diagnostic — which
line a learner *thinks* is broken tells you almost as much as whether
they find the real one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

DATA_PATH = Path(__file__).parent / "data" / "bughunt.json"


@dataclass
class BugSnippet:
    concept_id: str
    language: str
    code: str
    bug_line: int
    misconception: str
    hint: str
    fixed_code: str

    def public(self) -> dict:
        """What the learner sees before they answer: no spoilers."""
        return {
            "concept_id": self.concept_id,
            "language": self.language,
            "code": self.code,
            "num_lines": len(self.code.splitlines()),
        }


@dataclass
class BugHuntResult:
    correct_line: bool
    line_distance: int
    misconception: str
    fixed_code: str
    feedback: str


class BugHuntBank:
    def __init__(self, path: Path = DATA_PATH):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._snippets: Dict[str, BugSnippet] = {
            concept_id: BugSnippet(concept_id=concept_id, **fields) for concept_id, fields in raw.items()
        }

    def has(self, concept_id: str) -> bool:
        return concept_id in self._snippets

    def available_ids(self) -> list[str]:
        return list(self._snippets.keys())

    def get(self, concept_id: str) -> Optional[BugSnippet]:
        return self._snippets.get(concept_id)

    def check_guess(self, concept_id: str, guessed_line: int, hint_requested: bool = False) -> BugHuntResult:
        snippet = self.get(concept_id)
        if snippet is None:
            raise KeyError(f"no bug-hunt snippet for concept {concept_id!r}")

        distance = abs(guessed_line - snippet.bug_line)
        correct = distance == 0

        if correct:
            feedback = "That's the bug. Here's exactly why it's wrong:"
        elif distance == 1:
            feedback = "Very close — one line off. Here's what's actually broken:"
        else:
            base = "Not quite. " + (snippet.hint if hint_requested else "Try the hint, then look again.")
            feedback = base

        return BugHuntResult(
            correct_line=correct,
            line_distance=distance,
            misconception=snippet.misconception,
            fixed_code=snippet.fixed_code,
            feedback=feedback,
        )


bank = BugHuntBank()
