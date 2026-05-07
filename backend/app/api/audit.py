"""Audit middleware. Logs every request to a PHI-touching path with the
entity it accessed, the calling actor (X-User header for now), the
status code, and the duration.

We intentionally do not log request or response bodies. The point is a
who-touched-what trail; the bodies live in the regular structlog stream.
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.core.logging import get_logger
from app.storage.db import AuditRow, SessionLocal

log = get_logger(__name__)

# Map URL prefixes to (entity_type, regex extracting the id from the path).
PHI_ROUTES: list[tuple[str, str, re.Pattern[str]]] = [
    ("policies", "policy", re.compile(r"^/policies/([^/]+)")),
    ("patients", "patient", re.compile(r"^/patients/([^/]+)")),
    ("determinations", "determination", re.compile(r"^/determinations/([^/]+)")),
    ("determine", "determination", re.compile(r"^/determine(?:/stream)?$")),
    ("precheck", "precheck", re.compile(r"^/precheck$")),
]


def _classify(path: str) -> tuple[str | None, str | None]:
    for _, etype, pat in PHI_ROUTES:
        m = pat.match(path)
        if m:
            entity_id = m.group(1) if m.groups() else None
            return etype, entity_id
    return None, None


def install_audit(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        path = request.url.path
        entity_type, entity_id = _classify(path)
        if entity_type is None:
            return response

        actor = (
            getattr(request.state, "actor", None)
            or request.headers.get("x-user")
            or "anonymous"
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            with SessionLocal() as session:
                session.add(
                    AuditRow(
                        actor=actor,
                        method=request.method,
                        path=path,
                        status_code=response.status_code,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        duration_ms=duration_ms,
                    )
                )
                session.commit()
        except Exception as exc:
            # Audit is best-effort; never break the user request.
            log.warning("audit_write_failed", error=str(exc))
        return response
