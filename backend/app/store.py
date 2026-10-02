"""
Persistence for the Live Progress Map -- v2, on SQLAlchemy so it runs
against real PostgreSQL (set DATABASE_URL) instead of only a local
sqlite file. Public interface is unchanged from v1 on purpose: path.py,
main.py and the existing test suite all keep working without edits.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .db import Base, init_db
from .db import engine as default_engine
from .db import SessionLocal as default_session_local
from .models import Attempt, Mastery

STATUS_UNSEEN = "unseen"
STATUS_WEAK = "weak"
STATUS_MASTERED = "mastered"


@dataclass
class MasteryEntry:
    concept_id: str
    status: str
    updated_at: float


class ProgressStore:
    def __init__(self, database_url: str | None = None) -> None:
        """
        With no argument, uses the app-wide engine/session from db.py
        (DATABASE_URL env var, or local sqlite -- this is what main.py
        and the `store` singleton below use).

        Pass an explicit `database_url` (e.g. "sqlite:///:memory:") to
        get a fully isolated engine/session instead -- used by the test
        suite so TestPathEngine never touches the real demo database.
        """
        if database_url:
            self._engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
            )
            self._SessionLocal = sessionmaker(bind=self._engine, autoflush=False, autocommit=False)
            from . import models  # noqa: F401  (register models on Base.metadata)

            Base.metadata.create_all(bind=self._engine)
        else:
            init_db()
            self._engine = default_engine
            self._SessionLocal = default_session_local

    def dispose(self) -> None:
        """Close pooled connections. Only meaningful for stores created with
        an explicit `database_url` -- never disposes the shared app-wide
        engine, since other code may still be using it."""
        if self._engine is not default_engine:
            self._engine.dispose()

    @contextmanager
    def _session_scope(self):
        db = self._SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def mark(
        self,
        user_id: str,
        concept_id: str,
        status: str,
        mode: str,
        passed: bool,
        score: Optional[float] = None,
    ) -> None:
        now = time.time()
        with self._session_scope() as db:
            row = db.execute(
                select(Mastery).where(Mastery.user_id == user_id, Mastery.concept_id == concept_id)
            ).scalar_one_or_none()
            if row is None:
                row = Mastery(user_id=user_id, concept_id=concept_id, status=status, updated_at=now)
                db.add(row)
            else:
                row.status = status
                row.updated_at = now

            db.add(Attempt(user_id=user_id, concept_id=concept_id, mode=mode, passed=passed, score=score, created_at=now))

    def mastery_map(self, user_id: str, all_concept_ids: List[str]) -> Dict[str, MasteryEntry]:
        with self._session_scope() as db:
            rows = db.execute(select(Mastery).where(Mastery.user_id == user_id)).scalars().all()
            by_id = {r.concept_id: MasteryEntry(r.concept_id, r.status, r.updated_at) for r in rows}
        for cid in all_concept_ids:
            by_id.setdefault(cid, MasteryEntry(cid, STATUS_UNSEEN, 0.0))
        return by_id

    def recent_attempts(self, user_id: str, limit: int = 20) -> List[dict]:
        with self._session_scope() as db:
            rows = (
                db.execute(
                    select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.created_at.desc()).limit(limit)
                )
                .scalars()
                .all()
            )
        return [
            {"concept_id": r.concept_id, "mode": r.mode, "passed": r.passed, "score": r.score, "created_at": r.created_at}
            for r in rows
        ]


store = ProgressStore()
