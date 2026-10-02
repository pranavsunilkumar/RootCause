from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---- auth ----
class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None


class ForgotPasswordIn(BaseModel):
    username: str


class ForgotPasswordOut(BaseModel):
    message: str
    dev_reset_token: Optional[str] = None  # only populated when no email provider is configured


class ResetPasswordIn(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- gamification ----
class BadgeOut(BaseModel):
    code: str
    name: str
    description: str


class GamificationProfileOut(BaseModel):
    user_id: str
    points: int
    mastered_count: int
    passed_attempts: int
    current_streak: int
    badges: List[BadgeOut]


# ---- analytics ----
class ConceptStatOut(BaseModel):
    concept_id: str
    name: str
    attempts: int
    passes: int
    pass_rate: float


class ModeStatOut(BaseModel):
    mode: str
    attempts: int
    passes: int
    pass_rate: float


class AnalyticsOverviewOut(BaseModel):
    active_learners: int
    total_attempts: int
    overall_pass_rate: float
    total_mastered: int
    by_mode: List[ModeStatOut]
    hardest_concepts: List[ConceptStatOut]
    most_practiced_concepts: List[ConceptStatOut]


# ---- recommendations / RAG ----
class SearchHitOut(BaseModel):
    concept_id: str
    name: str
    score: float
    summary: str


class RecommendedConceptOut(BaseModel):
    concept_id: str
    name: str
    status: str
    reason: str
    related: List[SearchHitOut]


class AskIn(BaseModel):
    query: str = Field(..., min_length=1)


class AskOut(BaseModel):
    query: str
    answer: str
    sources: List[SearchHitOut]
    generated_by_llm: bool


class ConceptOut(BaseModel):
    id: str
    name: str
    prereqs: List[str]
    summary: str


class ChainStepOut(BaseModel):
    concept_id: str
    name: str
    question: str


class CheckNodeIn(BaseModel):
    user_id: str = Field(..., min_length=1)
    target_concept: str
    concept_id: str
    answer: str = ""


class GradeOut(BaseModel):
    score: float
    passed: bool
    matched: List[str]
    missing: List[str]
    feedback: str


class CheckNodeOut(BaseModel):
    concept_id: str
    name: str
    grade: GradeOut


class DiagnoseIn(BaseModel):
    user_id: str = Field(..., min_length=1)
    target_concept: str
    checks: List[CheckNodeOut]


class DiagnosisOut(BaseModel):
    target_concept: str
    broken_concept: str
    is_target_itself: bool
    steps_upstream: int
    lesson_summary: str
    lesson_key_points: List[str]
    ai_explanation: Optional[str] = None


class BugSnippetOut(BaseModel):
    concept_id: str
    language: str
    code: str
    num_lines: int


class BugGuessIn(BaseModel):
    user_id: str = Field(..., min_length=1)
    concept_id: str
    guessed_line: int
    hint_requested: bool = False


class BugGuessOut(BaseModel):
    correct_line: bool
    line_distance: int
    misconception: str
    fixed_code: str
    feedback: str


class TeachBackIn(BaseModel):
    user_id: str = Field(..., min_length=1)
    concept_id: str
    explanation: str


class TeachBackOut(BaseModel):
    concept_id: str
    grade: GradeOut
    followup_question: Optional[str] = None


class MasteryEntryOut(BaseModel):
    concept_id: str
    name: str
    status: str
    updated_at: float


class NextStepOut(BaseModel):
    concept_id: Optional[str] = None
    name: Optional[str] = None
    reason_code: str
    reason: str


class ProgressOut(BaseModel):
    user_id: str
    mastered: int
    weak: int
    unseen: int
    entries: List[MasteryEntryOut]
