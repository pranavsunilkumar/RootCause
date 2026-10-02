from __future__ import annotations

import time

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    masteries: Mapped[list["Mastery"]] = relationship(
        back_populates="user",
        primaryjoin="foreign(Mastery.user_id) == User.username",
        viewonly=True,
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="user",
        primaryjoin="foreign(Attempt.user_id) == User.username",
        viewonly=True,
    )


class Mastery(Base):
    """
    One row per (user_id, concept_id). user_id is a plain string, not a
    hard FK to User.id — this is deliberate: it lets anonymous demo
    learners (typed into the old free-text "Learner ID" box) and real
    logged-in users share exactly the same progress-tracking code path.
    Logged-in requests simply use the authenticated username as user_id.
    """

    __tablename__ = "mastery"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_mastery_user_concept"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    concept_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="unseen", nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)

    user: Mapped["User | None"] = relationship(
        back_populates="masteries",
        primaryjoin="foreign(Mastery.user_id) == User.username",
        viewonly=True,
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    concept_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # diagnose | bughunt | teachback
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)

    user: Mapped["User | None"] = relationship(
        back_populates="attempts",
        primaryjoin="foreign(Attempt.user_id) == User.username",
        viewonly=True,
    )


Index("ix_attempts_user_created", Attempt.user_id, Attempt.created_at)
