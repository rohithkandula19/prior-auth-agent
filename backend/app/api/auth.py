"""Tiny API-key auth.

Set API_KEYS in the environment as comma-separated key:actor pairs:
    API_KEYS=demo123:reviewer.alice,ops456:reviewer.bob

Set AUTH_REQUIRED=true to enforce. With auth disabled (default for local
dev), every request is treated as actor='anonymous' and audit logging
still works.

Reads the key from the X-API-Key header. Returns 401 on bad/missing key
when AUTH_REQUIRED=true. Stores the resolved actor name on
request.state.actor for the audit middleware to pick up.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Paths that don't need auth even when enforced.
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def _parse_keys(spec: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" in pair:
            k, actor = pair.split(":", 1)
            out[k.strip()] = actor.strip() or "anonymous"
        else:
            out[pair] = "anonymous"
    return out


def install_auth(app: FastAPI) -> None:
    keys = _parse_keys(settings.api_keys)
    enforce = settings.auth_required and bool(keys)
    log.info("auth_install", enforce=enforce, configured_keys=len(keys))

    @app.middleware("http")
    async def auth_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        actor = "anonymous"

        api_key = request.headers.get("x-api-key")
        if api_key:
            actor = keys.get(api_key, "unknown")

        if enforce and path not in PUBLIC_PATHS and not path.startswith("/static"):
            if not api_key or api_key not in keys:
                return Response(
                    content='{"detail":"missing or invalid X-API-Key"}',
                    status_code=401,
                    media_type="application/json",
                )

        # Stash for the audit middleware. Also expose via X-User if a real
        # user value came in; never trust X-User alone.
        request.state.actor = actor
        response = await call_next(request)
        return response
