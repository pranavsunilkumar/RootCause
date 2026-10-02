"""
Database layer. Real persistence via SQLAlchemy instead of the
hand-rolled sqlite3 store in the v1 backend.

- No DATABASE_URL set   -> sqlite file at backend/rootcause.db (zero
  config, exactly what you want for local dev and the hackathon demo).
- DATABASE_URL set      -> anything SQLAlchemy supports, in practice
  PostgreSQL on Render/Railway/Supabase/etc:
  postgresql+psycopg2://user:pass@host:5432/dbname

Render/Railway usually hand you a URL starting `postgres://` — SQLAlchemy
1.4+ / 2.x wants `postgresql://`, so we rewrite that prefix automatically.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_raw_url = os.environ.get("DATABASE_URL", "").strip()
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = _raw_url or "sqlite:///" + os.path.join(os.path.dirname(__file__), "..", "rootcause.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables that don't exist yet. Fine for a hackathon MVP;
    swap for Alembic migrations before this ever touches real user data."""
    from . import models  # noqa: F401  (import so models register on Base.metadata)

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Use as: `with session_scope() as db: ...` for scripts and tests."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: `db: Session = Depends(get_db)`."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
