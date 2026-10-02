"""
Seed a realistic demo state for user "demo-learner" so the Progress and
Path tabs show something meaningful the first time a judge opens the
app, instead of an empty graph.

Run from backend/:
    python scripts/seed_demo.py [user_id]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph import graph  # noqa: E402
from app.store import STATUS_MASTERED, STATUS_WEAK, store  # noqa: E402

# A believable partial journey: solid on the linear-algebra roots,
# genuinely weak on the chain rule -- which is exactly the kind of
# upstream break RootCause is built to catch before it wrecks
# backpropagation or attention.
MASTERED = ["vectors", "dot-product", "probability-basics", "matrix-multiplication"]
WEAK = ["chain-rule"]


def main(user_id: str) -> None:
    known = set(graph.all_ids())
    for cid in MASTERED:
        if cid in known:
            store.mark(user_id, cid, STATUS_MASTERED, mode="teachback", passed=True, score=0.9)
    for cid in WEAK:
        if cid in known:
            store.mark(user_id, cid, STATUS_WEAK, mode="diagnose", passed=False, score=0.2)
    print(f"Seeded {len(MASTERED)} mastered + {len(WEAK)} weak concept(s) for user {user_id!r}.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo-learner")
