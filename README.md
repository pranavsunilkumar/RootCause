# RootCause

**The AI tutor for AI/ML that finds what broke upstream.**

Team **Kuch bhi** — Pranav Muchalum & Ashutosh Kumar, DSATM — AI Build
Challenge 2026 (BFWAI/HACK 26), PS-03: *Personalized AI tutor for
learning AI*.

Most AI tutors re-explain whatever topic you asked about. RootCause
models AI/ML as a dependency graph, walks the prerequisite chain
underneath the concept you're stuck on, and finds the one node that's
*actually* broken — sometimes two or three steps upstream — instead of
re-explaining the thing you already asked about.

This repo is the full working prototype behind the idea deck: a FastAPI
backend implementing the diagnosis engine, bug-hunt challenges,
teach-back grading and path sequencing, and a React frontend for all
five learning modes plus a live progress map.

**Live standalone demo (no setup, runs entirely client-side):**
https://claude.ai/artifact/DHPDBaE116biX4zpyv7byu — a trimmed, single-file
port of the same graph/grading/path logic for judges to click through
immediately. The full app below is the real, extensible version.

---

## Architecture

```
rootcause/
├── backend/            FastAPI service — the diagnosis engine
│   ├── app/
│   │   ├── graph.py         concept DAG: load + validate + prereq_chain() + topo_order()
│   │   ├── grading.py       KeywordGrader (offline) / GeminiGrader (optional)
│   │   ├── diagnosis.py     walks the chain, finds the first broken node + ai_explain()
│   │   ├── bughunt.py       bug-hunt snippet bank + guess grading
│   │   ├── teachback.py     teach-back grading + naive-persona follow-ups
│   │   ├── path.py          personalized path: auto-sequences the next concept
│   │   ├── recommendations.py  broader recs + RAG-related concepts
│   │   ├── retrieval.py     TF-IDF concept search (the "R" in RAG)
│   │   ├── rag.py           retrieval + optional Gemini generation (the "AG")
│   │   ├── gamification.py  points + badges, computed from history
│   │   ├── analytics.py     platform-wide aggregate stats
│   │   ├── auth.py          password hashing (stdlib PBKDF2) + JWT
│   │   ├── db.py            SQLAlchemy engine/session (sqlite or Postgres)
│   │   ├── models.py        User / Mastery / Attempt ORM models
│   │   ├── store.py         progress store, now SQLAlchemy-backed
│   │   ├── schemas.py       pydantic request/response models
│   │   ├── main.py          FastAPI app / routes
│   │   └── data/
│   │       ├── concepts.json    20-node AI/ML concept graph
│   │       ├── bughunt.json     curated buggy snippets
│   │       └── followups.json   naive-persona follow-up questions
│   ├── scripts/
│   │   └── seed_demo.py     seeds a believable demo mastery state
│   └── tests/
│       └── test_logic.py    31 stdlib unittest cases (7 skip without SQLAlchemy)
└── frontend/             React + Vite SPA
    └── src/
        ├── api.js                fetch wrapper + JWT auth header
        ├── App.jsx                tab shell + auth state
        └── components/
            ├── Home.jsx
            ├── Login.jsx          optional register/login
            ├── Diagnose.jsx       the concept-graph diagnosis flow
            ├── BugHunt.jsx
            ├── TeachBack.jsx      includes voice input (Web Speech API)
            ├── Path.jsx           next-step + broader recommendations
            ├── Progress.jsx       live progress map
            ├── Leaderboard.jsx
            └── Analytics.jsx      platform dashboard, CSS bar charts
```

### How the diagnosis actually works

1. `graph.py` loads a hand-built dependency DAG (`concepts.json`) —
   e.g. `attention` needs `matrix-multiplication`, `softmax` and
   `dot-product`; `softmax` needs `probability-basics`; `matrix-
   multiplication` needs `vectors` and `dot-product`.
2. `prereq_chain(concept_id)` does a DFS post-order traversal of that
   node's transitive prerequisites, so the chain is always ordered from
   the most foundational concept to the target itself.
3. The frontend walks that chain one probe question at a time
   (`POST /api/diagnose/check`). Each answer is graded against a set of
   **keyword groups** — synonym sets for the ideas that answer needs to
   contain — via `KeywordGrader`, so grading works fully offline with
   zero API cost. If `GEMINI_API_KEY` is set, `GeminiGrader` is used
   instead for a more forgiving read of the learner's phrasing, with an
   automatic fallback to `KeywordGrader` on any API error.
4. The first node the learner fails is the diagnosis
   (`POST /api/diagnose`) — reported with how many steps upstream of
   the original topic it sits, plus a short targeted lesson.

Bug Hunt and Teach-Back reuse the same `KeywordGrader`/`GeminiGrader`
pair against curated bug explanations and per-concept key points, so
the whole app has exactly one grading code path to reason about.

### Personalized Path

`path.py` answers "what should this learner study next?"
(`GET /api/path/{user_id}`) with a simple, explainable policy built on
the graph's global topological order (`graph.topo_order()`):

1. If the learner has any **weak** concept, recommend the most
   foundational one — fixing it is most likely to unblock everything
   downstream, which is the whole thesis of RootCause.
2. Otherwise, recommend the most foundational **unseen** concept whose
   prerequisites are all already mastered — the next real frontier node.
3. If nothing is unlocked yet (brand-new learner), fall back to the
   most foundational unseen concept overall (always a true root).
4. If everything is mastered, there's nothing left to queue.

The frontend's **Path** tab shows the recommendation and reason, with a
one-click "Diagnose this concept" button that jumps straight into the
Diagnose tab pre-loaded on that concept.

---

## Running it locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env        # optional — only needed for GeminiGrader
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Run the test suite (no server needs to be running):

```bash
cd backend
python -m unittest tests.test_logic -v
```

Optional: seed a believable demo state (mastered linear-algebra roots,
weak on the chain rule) so Progress/Path aren't empty on first open:

```bash
cd backend
python scripts/seed_demo.py demo-learner
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # defaults to http://localhost:8000/api
npm run dev
```

Open http://localhost:5173. Start the backend first, or the app will
show a banner telling you it can't reach the API.

### Optional: Gemini-powered grading

Without an API key, RootCause runs entirely offline on the keyword
grader above — this is the default and what the demo should rely on.
To turn on richer, LLM-graded feedback, set `GEMINI_API_KEY` in
`backend/.env` (or your shell) before starting the backend. No code
changes needed — `get_default_grader()` picks the right grader
automatically, and every call degrades gracefully back to the keyword
grader if the API errors or the key is missing.

---

## Deploying

- **Backend** — `render.yaml` (repo root) and `backend/Procfile` deploy
  the FastAPI service to Render or any Heroku-style platform as-is.
  Set `GEMINI_API_KEY` in the dashboard if you want `GeminiGrader`;
  otherwise leave it unset and `KeywordGrader` runs, no config needed.
- **Frontend** — `frontend/vercel.json` deploys the Vite build to
  Vercel/Netlify. Set `VITE_API_BASE` to your deployed backend's
  `/api` URL as a build-time env var.

**Connecting the two once both are deployed:**
1. Deploy the backend first (Render/Railway); copy its public URL,
   e.g. `https://rootcause-api.onrender.com`.
2. In Vercel's project settings → Environment Variables, set
   `VITE_API_BASE=https://rootcause-api.onrender.com/api`, then
   redeploy the frontend (Vite bakes env vars in at build time, so a
   redeploy is required after changing this).
3. `main.py`'s CORS middleware allows all origins (`allow_origins=["*"]`)
   for demo simplicity — tighten it to your actual frontend domain
   before this is anything more than a hackathon submission.

## Extending the concept graph

Everything content-related lives in `backend/app/data/`:

- **`concepts.json`** — add a node with `id`, `name`, `prereqs` (a list
  of existing ids), a short `summary`, 2–3 `key_points`, and a `probe`
  (a question plus keyword groups — one group per idea the answer
  needs to hit).
- **`bughunt.json`** — optional, keyed by `concept_id`: a `code`
  snippet, the 1-indexed `bug_line`, a `misconception` explanation, a
  `hint`, and `fixed_code`.
- **`followups.json`** — optional, keyed by `concept_id` then by the
  exact `key_points` string it responds to: a naive-persona follow-up
  question. Any key point without a curated entry falls back to a
  generic "wait, can you explain: …" question.

`graph.py` validates on startup that every `prereqs` id exists and that
the graph has no cycles, so a bad edit fails fast with a clear error
instead of silently breaking the diagnosis flow.

---

## What's implemented vs. the pitch deck

| Deck slide | Status |
|---|---|
| Concept-Graph Diagnosis | ✅ `diagnosis.py` + `/api/diagnose*` |
| Bug Hunt Challenges | ✅ `bughunt.py` + `/api/bughunt*` (6 curated snippets) |
| Teach-Back Grading | ✅ `teachback.py` + `/api/teachback` |
| Personalized Path | ✅ `path.py` + `/api/path/{user_id}`, `Path.jsx` |
| Live Progress Map | ✅ `Progress.jsx` + `/api/progress/{user_id}` |

All five features from the pitch deck are implemented end to end —
backend logic, API, and a wired-up UI for each.

---

## v2: production features

Beyond the pitch deck's five features, the backend now also has:

| Feature | Module | Endpoint(s) |
|---|---|---|
| User login/authentication | `auth.py`, `models.py` (`User`) | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| PostgreSQL (was in-memory/sqlite-only) | `db.py`, `models.py`, `store.py` | — (used everywhere) |
| AI-powered diagnosis explanations | `diagnosis.py` (`ai_explain`) | `POST /api/diagnose` → `ai_explanation` field |
| RAG-based concept retrieval | `retrieval.py` (retrieval) + `rag.py` (generation) | `GET /api/search`, `POST /api/ask` |
| Learning recommendations | `recommendations.py` | `GET /api/recommendations/{user_id}` |
| Leaderboard & gamification | `gamification.py` | `GET /api/leaderboard`, `GET /api/gamification/{user_id}` |
| Analytics dashboard | `analytics.py` | `GET /api/analytics/overview` |
| Voice-based teaching assessment | frontend only — `TeachBack.jsx` | (browser Web Speech API → same `/api/teachback`) |
| Personalized learning paths | `path.py` + `recommendations.py` | `GET /api/path/{user_id}`, `GET /api/recommendations/{user_id}` |

**Auth model, deliberately hybrid:** every mutating endpoint still
accepts a free-text `user_id` for anonymous/demo use (unchanged from
v1) — but if a valid JWT is sent, the authenticated username silently
overrides it, so logged-in progress/leaderboard entries can't be
spoofed while anonymous mode keeps working with zero setup.

**RAG, honestly:** `retrieval.py` is real TF-IDF cosine similarity over
the concept graph — no vector DB, no embeddings API, so it's identical
offline and in production. `rag.py` is the generation half: it grounds
a Gemini prompt in the top retrieved concepts, and falls back to
returning those concepts' raw summaries (no LLM call) when
`GEMINI_API_KEY` isn't set.

**Voice assessment, honestly:** this uses the browser's built-in
`SpeechRecognition` API (Chrome/Edge) to transcribe speech into the
same explanation box Teach-Back already grades — no paid speech-to-text
API, no backend changes. Firefox/Safari users get a clear message and
can still type.

**What I could and couldn't execute-test:** `retrieval.py` is pure
stdlib and has real unit tests (`TestRetrieval` in `test_logic.py`) that
pass. `db.py`, `models.py`, `store.py`, `auth.py`, `gamification.py`,
`analytics.py` and the new `main.py` routes need SQLAlchemy/FastAPI,
which weren't installable in the sandbox this was built in (no network
access) — they're written against standard, well-documented patterns,
but **you should run `pip install -r requirements.txt` and the test
suite yourself** before trusting this in front of judges. The test
suite skips (not silently ignores) anything it can't verify, and says
exactly why:

```bash
cd backend
python -m unittest tests.test_logic -v
```

## DevOps: Docker, CI/CD, security

- **Docker:** `backend/Dockerfile` (non-root user, Postgres driver built
  in) and `frontend/Dockerfile` (multi-stage: Vite build → nginx serve).
  One command for the whole stack locally:
  ```bash
  docker compose up --build
  ```
  Frontend on `:5173`, backend on `:8000`, Postgres on `:5432`.
- **CI/CD:** `.github/workflows/ci.yml` — on every push/PR: backend
  compile-check + full test suite, frontend build, both Docker images
  build. Push this repo to GitHub and it runs automatically, no setup.
- **Security:** rate limiting + security headers + env-based CORS
  (`backend/app/security.py`), new API-level tests
  (`tests/test_api.py`) covering auth, spoofing protection, and the
  rate limiter itself. Full OWASP Top 10 mapping — what's covered, what
  isn't — in `SECURITY.md`. **Read it before any real deploy**, it's
  honest about the gaps.
- **Design system:** `DESIGN.md` — color/type/spacing tokens, component
  patterns, accessibility notes.

### Testing against real PostgreSQL locally

```bash
docker compose up -d          # starts Postgres on localhost:5432
export DATABASE_URL=postgresql://rootcause:rootcause@localhost:5432/rootcause
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
```

### New environment variables

See `backend/.env.example`. Notably: `DATABASE_URL` (empty = local
sqlite, set = PostgreSQL), `JWT_SECRET` (change before any real
deploy), `JWT_EXPIRES_SECONDS`.

### Railway deploy (alternative to Render)

`railway.json` at the repo root does the same job as `render.yaml` —
point Railway at the repo, it builds and runs the backend automatically.
Add a Railway PostgreSQL plugin and it sets `DATABASE_URL` for you.

The 20-node concept graph currently covers linear algebra fundamentals
through transformers — enough to fully demo backpropagation and
attention diagnoses multiple steps upstream, exactly as pitched.
