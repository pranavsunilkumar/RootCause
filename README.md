# RootCause

**The AI tutor for AI/ML that finds what broke upstream.**

### 🔗 [**Live Demo →**](https://root-cause-five.vercel.app/)

*(Backend may take 30–60s to wake up on the first request — it's on Render's free tier, which sleeps when idle.)*

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
five learning modes plus a live 3D progress map.

<!--
  📸 ADD SCREENSHOT: Home page hero + mode cards
  Save as: docs/screenshots/home.png
  Then uncomment the line below:
  ![RootCause home page](docs/screenshots/home.png)
-->

---

## Screenshots

<!--
  Capture these from the live demo (or `npm run dev` locally) and drop
  the files into docs/screenshots/, then uncomment each line below.
  Suggested shots:
    1. home.png        — the hero + 6 mode cards on Home
    2. diagnose.png     — mid-diagnosis, a probe question with feedback
    3. galaxy.png        — the 3D Concept Galaxy on Progress, ideally with
                           Energy Flow or Fog of War toggled on
    4. bughunt.png      — a bug-hunt code snippet with a guess submitted
    5. teachback.png     — a teach-back explanation + grading feedback
    6. profile.png        — profile page with points/badges/streak
-->

| | |
|---|---|
| ![Home](docs/screenshots/home.png) | ![Diagnose](docs/screenshots/diagnose.png) |
| ![3D Concept Galaxy](docs/screenshots/galaxy.png) | ![Bug Hunt](docs/screenshots/bughunt.png) |
| ![Teach-Back](docs/screenshots/teachback.png) | ![Profile](docs/screenshots/profile.png) |

---

## What's in it

Five learning modes, all backed by one 20-node AI/ML concept graph
(linear algebra fundamentals through transformers/attention):

- **🧠 Diagnose** — pick a concept you're stuck on, answer a couple of
  quick checks on its prerequisites, and RootCause finds the exact node
  that broke, however many steps upstream it sits.
- **🐞 Bug Hunt** — a short code snippet with one deliberate
  misconception-bug. Find the line, get the explanation.
- **🗣️ Teach-Back** — explain a concept in your own words (typed or
  spoken via the browser's voice input). Graded against the key ideas,
  with a natural follow-up question if something's missing.
- **🧭 Path** — auto-sequences the next concept to study: the weakest
  foundational node if you have one, otherwise the next concept you're
  actually ready for.
- **📊 Progress** — a live **3D Concept Galaxy** (built with Three.js)
  showing every concept you've touched, with:
  - **Glow halos** that brighten as concepts go from unseen → weak → mastered
  - **⚡ Energy Flow** — animated particles traveling from mastered
    concepts outward along the dependency graph
  - **🌫 Fog of War** — concepts whose prerequisites aren't mastered yet
    render as dim, unlabeled silhouettes until you unlock them
  - A clickable breadcrumb trail showing the dependency path to any
    selected node

Plus **gamification** (points, streaks, badges, leaderboard) and an
**analytics dashboard** with platform-wide stats, all computed live
from your actual attempt history — no separate state to keep in sync.

No login or signup required — just pick a display name on first visit
(saved locally in your browser) and go.

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
│   │   ├── auth.py          password hashing (stdlib PBKDF2) + JWT (optional accounts)
│   │   ├── security.py      rate limiting + security headers + CORS config
│   │   ├── db.py            SQLAlchemy engine/session (sqlite or Postgres)
│   │   ├── models.py        User / Mastery / Attempt ORM models
│   │   ├── store.py         progress store, SQLAlchemy-backed
│   │   ├── schemas.py       pydantic request/response models
│   │   ├── main.py          FastAPI app / routes
│   │   └── data/
│   │       ├── concepts.json    20-node AI/ML concept graph
│   │       ├── bughunt.json     curated buggy snippets
│   │       └── followups.json   naive-persona follow-up questions
│   ├── scripts/
│   │   └── seed_demo.py     seeds a believable demo mastery state
│   └── tests/
│       ├── test_logic.py    stdlib unittest cases for the core logic
│       └── test_api.py      FastAPI TestClient tests (auth, rate limiting, etc.)
└── frontend/             React + Vite SPA
    └── src/
        ├── api.js                fetch wrapper + JWT auth header (optional accounts)
        ├── App.jsx                tab shell + local display-name gate
        └── components/
            ├── Home.jsx            hero, mode cards, contact section
            ├── Diagnose.jsx       the concept-graph diagnosis flow
            ├── BugHunt.jsx
            ├── TeachBack.jsx      includes voice input (Web Speech API)
            ├── Path.jsx           next-step + broader recommendations
            ├── Progress.jsx       3D Concept Galaxy (Three.js) + live progress map
            ├── Profile.jsx         points, badges, streak, change-name
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

### The 3D Concept Galaxy

`Progress.jsx` renders the full concept graph as a navigable 3D scene
(drag to orbit, scroll to zoom, click a node for details):

- Node **color and glow intensity** reflect status: gray/faint for
  unseen, amber for weak, green and brightly glowing for mastered.
- **⚡ Energy Flow** toggle animates a particle traveling along every
  edge whose source concept is mastered — a visual metaphor for
  understanding "flowing outward" into what it unlocks.
- **🌫 Fog of War** toggle hides concepts (and their incoming edges)
  whose prerequisites aren't fully mastered yet, rendering them as dim
  silhouettes with a "?" marker — the graph reveals itself as you
  actually unlock concepts, rather than showing everything at once.
- Clicking a node (or an item in the breadcrumb path) flies the camera
  to it and shows a summary card with a one-click "Diagnose this node"
  button.

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
python -m unittest tests.test_api -v
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

This repo is already deployed and configured for **Render** (backend)
+ **Vercel** (frontend):

- **Backend** — `render.yaml` (repo root) deploys the FastAPI service
  as a Render Blueprint: connect the repo, Render reads the YAML,
  prompts for the secret env vars, and builds/starts it automatically.
- **Frontend** — `frontend/vercel.json` deploys the Vite build to
  Vercel. Set the **Root Directory** to `frontend` when importing the
  project.

**Connecting the two:**
1. Deploy the backend first; copy its public URL,
   e.g. `https://rootcause-api-xxxx.onrender.com`.
2. On Vercel → Project Settings → Environment Variables, set
   `VITE_API_BASE=https://rootcause-api-xxxx.onrender.com/api`
   (type **Plain Text/Config**, *not* Secret — `VITE_`-prefixed vars
   are meant to be read by the browser, and Vercel won't let you save
   a `VITE_` variable as a Secret). Then **redeploy** — Vite bakes env
   vars in at build time, so just saving the variable isn't enough.
3. On Render → your service → Environment, set `ALLOWED_ORIGINS` to
   your exact Vercel domain (no trailing slash), e.g.
   `ALLOWED_ORIGINS=https://root-cause-xxxx.vercel.app`. Without this,
   `main.py`'s CORS middleware falls back to `allow_origins=["*"]`,
   which works but should be tightened for anything beyond a demo.

**Common gotcha:** if the deployed frontend loads but no data shows up
anywhere (Progress, Diagnose, concept lists all empty), open DevTools →
Network tab. A CORS error or a request to the wrong hostname almost
always means `VITE_API_BASE` is stale (needs a redeploy after editing)
or doesn't match the backend's real URL exactly.

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
| Live Progress Map | ✅ `Progress.jsx` — now a 3D Concept Galaxy + `/api/progress/{user_id}` |

All five features from the pitch deck are implemented end to end —
backend logic, API, and a wired-up UI for each.

---

## v2: production features

Beyond the pitch deck's five features, the backend also has:

| Feature | Module | Endpoint(s) |
|---|---|---|
| Optional user accounts | `auth.py`, `models.py` (`User`) | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| PostgreSQL (was in-memory/sqlite-only) | `db.py`, `models.py`, `store.py` | — (used everywhere) |
| AI-powered diagnosis explanations | `diagnosis.py` (`ai_explain`) | `POST /api/diagnose` → `ai_explanation` field |
| RAG-based concept retrieval | `retrieval.py` (retrieval) + `rag.py` (generation) | `GET /api/search`, `POST /api/ask` |
| Learning recommendations | `recommendations.py` | `GET /api/recommendations/{user_id}` |
| Leaderboard & gamification | `gamification.py` | `GET /api/leaderboard`, `GET /api/gamification/{user_id}` |
| Analytics dashboard | `analytics.py` | `GET /api/analytics/overview` |
| Voice-based teaching assessment | frontend only — `TeachBack.jsx` | (browser Web Speech API → same `/api/teachback`) |
| Personalized learning paths | `path.py` + `recommendations.py` | `GET /api/path/{user_id}`, `GET /api/recommendations/{user_id}` |

**Identity, deliberately simple:** the live UI uses a free-text display
name saved to `localStorage` — no signup, no password, zero friction
for a demo. The backend's full JWT-based account system
(`/api/auth/*`) still exists and works end to end if you want to wire
real accounts back in; every mutating endpoint already accepts an
authenticated JWT (which silently overrides any `user_id` sent in the
body, so progress can't be spoofed) and falls back to the free-text
`user_id` when there's no token, so both modes share one code path.

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

Run the test suite yourself before trusting this in front of judges:

```bash
cd backend
python -m unittest tests.test_logic -v
python -m unittest tests.test_api -v
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
  (`backend/app/security.py`), API-level tests (`tests/test_api.py`)
  covering auth, spoofing protection, and the rate limiter itself. Full
  OWASP Top 10 mapping — what's covered, what isn't — in `SECURITY.md`.
  **Read it before any real deploy**, it's honest about the gaps.
- **Design system:** `DESIGN.md` — color/type/spacing tokens, component
  patterns, accessibility notes.

### Testing against real PostgreSQL locally

```bash
docker compose up -d          # starts Postgres on localhost:5432
export DATABASE_URL=postgresql://rootcause:rootcause@localhost:5432/rootcause
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Environment variables

See `backend/.env.example`. Notably:

- `GEMINI_API_KEY` / `GEMINI_MODEL` — optional, enables `GeminiGrader` +
  LLM-generated RAG answers + AI diagnosis explanations
- `DATABASE_URL` — empty = local sqlite, set = PostgreSQL
- `JWT_SECRET` — change before any real deploy
- `JWT_EXPIRES_SECONDS`
- `ALLOWED_ORIGINS` — comma-separated list of allowed frontend origins for CORS

### Railway deploy (alternative to Render)

`railway.json` at the repo root does the same job as `render.yaml` —
point Railway at the repo, it builds and runs the backend automatically.
Add a Railway PostgreSQL plugin and it sets `DATABASE_URL` for you.

The 20-node concept graph currently covers linear algebra fundamentals
through transformers — enough to fully demo backpropagation and
attention diagnoses multiple steps upstream, exactly as pitched.

---

## Contact

- 📧 **Email:** pranavweb18@gmail.com
- 💻 **GitHub:** [github.com/pranavsunilkumar/RootCause](https://github.com/pranavsunilkumar/RootCause)
- 🔗 **LinkedIn:** [linkedin.com/in/pranav-muchalum](https://www.linkedin.com/in/pranav-muchalum-25a9a8323/)
