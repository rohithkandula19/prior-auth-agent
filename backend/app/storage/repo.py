"""DB-backed repositories. Each Pydantic model is stored as a JSON blob
keyed by id, so schema changes do not need migrations.

Falls back to an in-memory map automatically if the database connection
fails on startup (useful for the offline test/eval paths).
"""

from __future__ import annotations

from threading import RLock
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.schemas.determination import Determination
from app.schemas.patient import Patient
from app.schemas.policy import Policy
from app.storage.db import (
    DeterminationRow,
    PatientRow,
    PolicyRow,
    PolicyVersionRow,
    SessionLocal,
    healthcheck,
)

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class _MemoryRepo(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._lock = RLock()

    def put(self, key: str, value: T) -> T:
        with self._lock:
            self._items[key] = value
        return value

    def get(self, key: str) -> T | None:
        with self._lock:
            return self._items.get(key)

    def list(self) -> list[T]:
        with self._lock:
            return list(self._items.values())

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._items.pop(key, None) is not None


class _PolicyRepo:
    def put(self, key: str, value: Policy) -> Policy:
        payload = value.model_dump(mode="json")
        with SessionLocal() as session:  # type: Session
            row = session.get(PolicyRow, key)
            if row:
                row.data = payload
            else:
                session.add(PolicyRow(id=key, data=payload))
            # Append a version row each time put() is called.
            last = (
                session.query(PolicyVersionRow)
                .filter(PolicyVersionRow.policy_id == key)
                .order_by(PolicyVersionRow.version.desc())
                .first()
            )
            next_v = (last.version + 1) if last else 1
            session.add(PolicyVersionRow(policy_id=key, version=next_v, data=payload))
            session.commit()
        return value

    def get(self, key: str) -> Policy | None:
        with SessionLocal() as session:
            row = session.get(PolicyRow, key)
            return Policy.model_validate(row.data) if row else None

    def list(self) -> list[Policy]:
        with SessionLocal() as session:
            rows = session.query(PolicyRow).order_by(PolicyRow.created_at.desc()).all()
            return [Policy.model_validate(r.data) for r in rows]

    def delete(self, key: str) -> bool:
        with SessionLocal() as session:
            row = session.get(PolicyRow, key)
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True


class _PatientRepo:
    def put(self, key: str, value: Patient) -> Patient:
        with SessionLocal() as session:
            row = session.get(PatientRow, key)
            if row:
                row.data = value.model_dump(mode="json")
            else:
                session.add(PatientRow(id=key, data=value.model_dump(mode="json")))
            session.commit()
        return value

    def get(self, key: str) -> Patient | None:
        with SessionLocal() as session:
            row = session.get(PatientRow, key)
            return Patient.model_validate(row.data) if row else None

    def list(self) -> list[Patient]:
        with SessionLocal() as session:
            rows = session.query(PatientRow).order_by(PatientRow.created_at.desc()).all()
            return [Patient.model_validate(r.data) for r in rows]

    def delete(self, key: str) -> bool:
        with SessionLocal() as session:
            row = session.get(PatientRow, key)
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True


class _DeterminationRepo:
    def put(self, key: str, value: Determination) -> Determination:
        payload = value.model_dump(mode="json")
        with SessionLocal() as session:
            row = session.get(DeterminationRow, key)
            if row:
                row.data = payload
                row.policy_id = value.policy_id
                row.patient_id = value.patient_id
                row.decision = value.decision
            else:
                session.add(
                    DeterminationRow(
                        id=key,
                        policy_id=value.policy_id,
                        patient_id=value.patient_id,
                        decision=value.decision,
                        data=payload,
                    )
                )
            session.commit()
        return value

    def get(self, key: str) -> Determination | None:
        with SessionLocal() as session:
            row = session.get(DeterminationRow, key)
            return Determination.model_validate(row.data) if row else None

    def list(self) -> list[Determination]:
        with SessionLocal() as session:
            rows = (
                session.query(DeterminationRow)
                .order_by(DeterminationRow.created_at.desc())
                .all()
            )
            return [Determination.model_validate(r.data) for r in rows]

    def delete(self, key: str) -> bool:
        with SessionLocal() as session:
            row = session.get(DeterminationRow, key)
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True


# Pick DB-backed repos if the connection is healthy; otherwise fall back to
# in-memory maps so unit tests and offline scripts keep working.
if healthcheck():
    policy_repo: object = _PolicyRepo()
    patient_repo: object = _PatientRepo()
    determination_repo: object = _DeterminationRepo()
    log.info("repos_db_backed")
else:
    policy_repo = _MemoryRepo[Policy]()
    patient_repo = _MemoryRepo[Patient]()
    determination_repo = _MemoryRepo[Determination]()
    log.warning("repos_memory_fallback")
