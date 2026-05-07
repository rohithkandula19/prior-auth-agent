"""Read-only audit log endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.storage.db import AuditRow, SessionLocal

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEntry(BaseModel):
    id: int
    ts: str
    actor: str
    method: str
    path: str
    status_code: int
    entity_type: str | None
    entity_id: str | None
    duration_ms: int


@router.get("", response_model=list[AuditEntry])
async def list_audit(limit: int = Query(100, ge=1, le=500)) -> list[AuditEntry]:
    with SessionLocal() as session:
        rows = (
            session.query(AuditRow)
            .order_by(AuditRow.ts.desc())
            .limit(limit)
            .all()
        )
        return [
            AuditEntry(
                id=r.id,
                ts=r.ts.isoformat(),
                actor=r.actor,
                method=r.method,
                path=r.path,
                status_code=r.status_code,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                duration_ms=r.duration_ms,
            )
            for r in rows
        ]
