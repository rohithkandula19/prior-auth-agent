"""SQLAlchemy engine + session factory and ORM models.

Storage is intentionally simple: each row is an id plus a JSON blob holding
the full Pydantic model. This keeps the schema stable across model edits
and lets a future migration project rich columns out as needed. Works
identically against SQLite (default) and Postgres (set DATABASE_URL).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        # Make sure the parent directory exists for file-based SQLite.
        prefix = "sqlite:///"
        if url.startswith(prefix):
            path = url[len(prefix):]
            if path and not path.startswith(":memory:"):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, future=True, connect_args={"check_same_thread": False})
    return create_engine(url, future=True, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class PolicyRow(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PatientRow(Base):
    __tablename__ = "patients"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeterminationRow(Base):
    __tablename__ = "determinations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String, index=True, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditRow(Base):
    """Append-only audit log of PHI-touching API calls."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    actor: Mapped[str] = mapped_column(String, default="anonymous", index=True)
    method: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    duration_ms: Mapped[int] = mapped_column(default=0)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    log.info("db_initialized", url=settings.database_url)


def healthcheck() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.warning("db_healthcheck_failed", error=str(exc))
        return False


def get_session() -> Session:
    return SessionLocal()
