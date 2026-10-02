"""
RootCause API.

Run locally:
    uvicorn app.main:app --reload --port 8000

Interactive docs then live at http://localhost:8000/docs

Endpoints (all under /api):
    GET  /health
    GET  /concepts
    GET  /concepts/{concept_id}/chain
    POST /diagnose/check
    POST /diagnose
    GET  /bughunt
    GET  /bughunt/{concept_id}
    POST /bughunt/guess
    POST /teachback
    GET  /path/{user_id}
    GET  /progress/{user_id}
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import analytics, gamification, schemas as S
from .auth import create_access_token, create_reset_token, get_current_user_optional, hash_password, verify_password, verify_reset_token
from .security import RateLimitMiddleware, SecurityHeadersMiddleware, get_allowed_origins
from .bughunt import bank as bughunt_bank
from .db import get_db
from .diagnosis import DiagnosisEngine, NodeCheck
from .grading import GradeResult
from .graph import graph
from .models import User
from .path import path_engine
from .rag import rag_engine
from .recommendations import recommendation_engine
from .retrieval import index as concept_index
from .store import STATUS_MASTERED, STATUS_WEAK, store
from .teachback import TeachBackEngine

app = FastAPI(title="RootCause API", version="1.0.0")

# Starlette applies middleware outer-to-inner in the REVERSE of add order,
# so CORS is added last to stay outermost -- otherwise a 429 from
# RateLimitMiddleware never reaches CORSMiddleware and shows up in the
# browser as an opaque CORS failure instead of a clean 429 response.
app.add_middleware(
    RateLimitMiddleware,
    limited_prefixes=("/api/auth/", "/api/diagnose", "/api/bughunt/guess", "/api/teachback"),
    limit=20,
    window_seconds=60,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),  # set ALLOWED_ORIGINS env var in production; "*" is the dev-only fallback
    allow_methods=["*"],
    allow_headers=["*"],
)

diagnosis_engine = DiagnosisEngine(concept_graph=graph)
teachback_engine = TeachBackEngine(concept_graph=graph)


def _resolve_user_id(body_user_id: str, current_user: User | None) -> str:
    """If the caller is logged in, their username is the canonical user_id
    (overriding whatever the client sent), so points/progress can't be
    spoofed onto someone else's account. Anonymous callers keep working
    exactly as in v1, using the free-text id they supplied."""
    return current_user.username if current_user else body_user_id


@app.post("/api/auth/register", response_model=S.TokenOut)
def register(body: S.RegisterIn, db: Session = Depends(get_db)):
    if db.execute(select(User).where(User.username == body.username)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(username=body.username, email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.username)
    return S.TokenOut(access_token=token, user=S.UserOut(id=user.id, username=user.username, email=user.email))


@app.post("/api/auth/login", response_model=S.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == form.username)).scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(user.username)
    return S.TokenOut(access_token=token, user=S.UserOut(id=user.id, username=user.username, email=user.email))


@app.post("/api/auth/forgot-password", response_model=S.ForgotPasswordOut)
def forgot_password(body: S.ForgotPasswordIn, db: Session = Depends(get_db)):
    """
    No email provider is wired up (that needs SMTP/SendGrid/etc. credentials
    this project doesn't have), so this is honest about it: in dev mode it
    hands the reset token straight back in the response instead of pretending
    to email it. Wire in a real mailer and stop returning dev_reset_token
    before this touches real users.
    """
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    # Same response whether the username exists or not -- don't leak which
    # usernames are registered.
    if user is None:
        return S.ForgotPasswordOut(message="If that account exists, a reset link has been issued.")

    token = create_reset_token(user.username)
    email_configured = False  # flip this once a real mailer is wired in
    if email_configured:
        return S.ForgotPasswordOut(message="If that account exists, a reset link has been issued.")
    return S.ForgotPasswordOut(
        message="No email provider is configured -- here's your reset token directly (dev mode only).",
        dev_reset_token=token,
    )


@app.post("/api/auth/reset-password", response_model=S.TokenOut)
def reset_password(body: S.ResetPasswordIn, db: Session = Depends(get_db)):
    username = verify_reset_token(body.reset_token)
    if not username:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User no longer exists")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    token = create_access_token(user.username)
    return S.TokenOut(access_token=token, user=S.UserOut(id=user.id, username=user.username, email=user.email))


@app.get("/api/auth/me", response_model=S.UserOut)
def me(current_user: User | None = Depends(get_current_user_optional)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return S.UserOut(id=current_user.id, username=current_user.username, email=current_user.email)


@app.get("/api/health")
def health():
    return {"status": "ok", "concepts_loaded": len(graph)}


@app.get("/api/concepts", response_model=list[S.ConceptOut])
def list_concepts():
    return graph.to_public_list()


@app.get("/api/concepts/{concept_id}/chain", response_model=list[S.ChainStepOut])
def get_chain(concept_id: str):
    _require_concept(concept_id)
    return [S.ChainStepOut(concept_id=s.concept_id, name=s.name, question=s.question) for s in diagnosis_engine.chain_for(concept_id)]


@app.post("/api/diagnose/check", response_model=S.CheckNodeOut)
def diagnose_check(body: S.CheckNodeIn, current_user: User | None = Depends(get_current_user_optional)):
    _require_concept(body.target_concept)
    _require_concept(body.concept_id)
    user_id = _resolve_user_id(body.user_id, current_user)

    result = diagnosis_engine.check_node(body.concept_id, body.answer)

    store.mark(
        user_id=user_id,
        concept_id=body.concept_id,
        status=STATUS_MASTERED if result.result.passed else STATUS_WEAK,
        mode="diagnose",
        passed=result.result.passed,
        score=result.result.score,
    )

    return S.CheckNodeOut(concept_id=result.concept_id, name=result.name, grade=_grade_out(result.result))


@app.post("/api/diagnose", response_model=S.DiagnosisOut)
def diagnose(body: S.DiagnoseIn, current_user: User | None = Depends(get_current_user_optional)):
    _require_concept(body.target_concept)
    user_id = _resolve_user_id(body.user_id, current_user)

    node_checks = [
        NodeCheck(
            concept_id=c.concept_id,
            name=c.name,
            result=GradeResult(
                score=c.grade.score,
                passed=c.grade.passed,
                matched=c.grade.matched,
                missing=c.grade.missing,
                feedback=c.grade.feedback,
            ),
        )
        for c in body.checks
    ]

    diagnosis = diagnosis_engine.diagnose_from_checks(body.target_concept, node_checks)

    is_target_itself = diagnosis.broken_concept == body.target_concept and diagnosis.steps_upstream == 0
    if not is_target_itself:
        store.mark(
            user_id=user_id,
            concept_id=diagnosis.broken_concept,
            status=STATUS_WEAK,
            mode="diagnose",
            passed=False,
        )

    # Note: this endpoint only receives graded results, not the learner's raw
    # answer text, so the AI explanation is grounded in the diagnosis itself
    # rather than their exact wording. /api/diagnose/check is where the raw
    # answer is available, if you want to thread it through for an even more
    # personalized explanation later.
    ai_explanation = diagnosis_engine.ai_explain(diagnosis)

    return S.DiagnosisOut(
        target_concept=diagnosis.target_concept,
        broken_concept=diagnosis.broken_concept,
        is_target_itself=is_target_itself,
        steps_upstream=diagnosis.steps_upstream,
        lesson_summary=diagnosis.lesson_summary,
        lesson_key_points=diagnosis.lesson_key_points,
        ai_explanation=ai_explanation,
    )


@app.get("/api/bughunt", response_model=list[str])
def list_bughunt_concepts():
    return bughunt_bank.available_ids()


@app.get("/api/bughunt/{concept_id}", response_model=S.BugSnippetOut)
def get_bughunt_snippet(concept_id: str):
    snippet = bughunt_bank.get(concept_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail=f"no bug-hunt challenge for {concept_id!r} yet")
    return S.BugSnippetOut(**snippet.public())


@app.post("/api/bughunt/guess", response_model=S.BugGuessOut)
def submit_bughunt_guess(body: S.BugGuessIn, current_user: User | None = Depends(get_current_user_optional)):
    if not bughunt_bank.has(body.concept_id):
        raise HTTPException(status_code=404, detail=f"no bug-hunt challenge for {body.concept_id!r}")
    user_id = _resolve_user_id(body.user_id, current_user)

    result = bughunt_bank.check_guess(body.concept_id, body.guessed_line, body.hint_requested)

    store.mark(
        user_id=user_id,
        concept_id=body.concept_id,
        status=STATUS_MASTERED if result.correct_line else STATUS_WEAK,
        mode="bughunt",
        passed=result.correct_line,
    )

    return S.BugGuessOut(
        correct_line=result.correct_line,
        line_distance=result.line_distance,
        misconception=result.misconception,
        fixed_code=result.fixed_code,
        feedback=result.feedback,
    )


@app.post("/api/teachback", response_model=S.TeachBackOut)
def submit_teachback(body: S.TeachBackIn, current_user: User | None = Depends(get_current_user_optional)):
    _require_concept(body.concept_id)
    user_id = _resolve_user_id(body.user_id, current_user)

    result = teachback_engine.grade(body.concept_id, body.explanation)

    store.mark(
        user_id=user_id,
        concept_id=body.concept_id,
        status=STATUS_MASTERED if result.grade.passed else STATUS_WEAK,
        mode="teachback",
        passed=result.grade.passed,
        score=result.grade.score,
    )

    return S.TeachBackOut(
        concept_id=result.concept_id,
        grade=_grade_out(result.grade),
        followup_question=result.followup_question,
    )


@app.get("/api/path/{user_id}", response_model=S.NextStepOut)
def next_step(user_id: str):
    """Personalized Path: what should this learner study next?"""
    step = path_engine.next_concept(user_id)
    name = graph.get(step.concept_id).name if step.concept_id else None
    return S.NextStepOut(concept_id=step.concept_id, name=name, reason_code=step.reason_code, reason=step.reason)


@app.get("/api/progress/{user_id}", response_model=S.ProgressOut)
def get_progress(user_id: str):
    all_ids = graph.all_ids()
    mastery = store.mastery_map(user_id, all_ids)

    entries = [
        S.MasteryEntryOut(
            concept_id=cid,
            name=graph.get(cid).name,
            status=entry.status,
            updated_at=entry.updated_at,
        )
        for cid, entry in mastery.items()
    ]
    entries.sort(key=lambda e: e.name)

    return S.ProgressOut(
        user_id=user_id,
        mastered=sum(1 for e in entries if e.status == STATUS_MASTERED),
        weak=sum(1 for e in entries if e.status == STATUS_WEAK),
        unseen=sum(1 for e in entries if e.status == "unseen"),
        entries=entries,
    )


@app.get("/api/gamification/{user_id}", response_model=S.GamificationProfileOut)
def gamification_profile(user_id: str, db: Session = Depends(get_db)):
    p = gamification.compute_profile(db, user_id, concept_graph=graph)
    return S.GamificationProfileOut(
        user_id=p.user_id,
        points=p.points,
        mastered_count=p.mastered_count,
        passed_attempts=p.passed_attempts,
        current_streak=p.current_streak,
        badges=[S.BadgeOut(code=b.code, name=b.name, description=b.description) for b in p.badges],
    )


@app.get("/api/leaderboard", response_model=list[S.GamificationProfileOut])
def leaderboard(limit: int = 20, db: Session = Depends(get_db)):
    profiles = gamification.leaderboard(db, concept_graph=graph, limit=limit)
    return [
        S.GamificationProfileOut(
            user_id=p.user_id,
            points=p.points,
            mastered_count=p.mastered_count,
            passed_attempts=p.passed_attempts,
            current_streak=p.current_streak,
            badges=[S.BadgeOut(code=b.code, name=b.name, description=b.description) for b in p.badges],
        )
        for p in profiles
    ]


@app.get("/api/analytics/overview", response_model=S.AnalyticsOverviewOut)
def analytics_overview(db: Session = Depends(get_db)):
    o = analytics.compute_overview(db, concept_graph=graph)
    return S.AnalyticsOverviewOut(
        active_learners=o.active_learners,
        total_attempts=o.total_attempts,
        overall_pass_rate=o.overall_pass_rate,
        total_mastered=o.total_mastered,
        by_mode=[S.ModeStatOut(**vars(m)) for m in o.by_mode],
        hardest_concepts=[S.ConceptStatOut(**vars(c)) for c in o.hardest_concepts],
        most_practiced_concepts=[S.ConceptStatOut(**vars(c)) for c in o.most_practiced_concepts],
    )


@app.get("/api/recommendations/{user_id}", response_model=list[S.RecommendedConceptOut])
def recommendations(user_id: str, limit: int = 5):
    picks = recommendation_engine.recommend(user_id, limit=limit)
    return [
        S.RecommendedConceptOut(
            concept_id=p.concept_id,
            name=p.name,
            status=p.status,
            reason=p.reason,
            related=[S.SearchHitOut(concept_id=h.concept_id, name=h.name, score=h.score, summary=h.summary) for h in p.related],
        )
        for p in picks
    ]


@app.get("/api/search", response_model=list[S.SearchHitOut])
def search_concepts(q: str, top_k: int = 5):
    hits = concept_index.search(q, top_k=top_k)
    return [S.SearchHitOut(concept_id=h.concept_id, name=h.name, score=h.score, summary=h.summary) for h in hits]


@app.post("/api/ask", response_model=S.AskOut)
def ask(body: S.AskIn):
    """RAG: retrieve grounding concepts, optionally generate a Gemini answer
    from them, fall back to the raw retrieved summaries otherwise."""
    result = rag_engine.answer(body.query)
    return S.AskOut(
        query=result.query,
        answer=result.answer,
        sources=[S.SearchHitOut(concept_id=h.concept_id, name=h.name, score=h.score, summary=h.summary) for h in result.sources],
        generated_by_llm=result.generated_by_llm,
    )


def _require_concept(concept_id: str) -> None:
    try:
        graph.get(concept_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown concept id: {concept_id!r}")


def _grade_out(g: GradeResult) -> S.GradeOut:
    return S.GradeOut(score=g.score, passed=g.passed, matched=g.matched, missing=g.missing, feedback=g.feedback)
