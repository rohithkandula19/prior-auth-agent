from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_audit,
    routes_batch,
    routes_determinations,
    routes_eval,
    routes_patients,
    routes_policies,
    routes_precheck,
)
from app.api.audit import install_audit
from app.api.auth import install_auth
from app.core.logging import configure_logging, get_logger
from app.storage.db import init_db

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_db()
    log.info("startup")
    yield
    log.info("shutdown")


app = FastAPI(
    title="Prior Authorization Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Order matters: middlewares run last-in-first-out per FastAPI. We want
# auth to set request.state.actor BEFORE audit reads it, so install audit
# first (it runs second per LIFO), then auth.
install_audit(app)
install_auth(app)

app.include_router(routes_policies.router)
app.include_router(routes_patients.router)
app.include_router(routes_determinations.router)
app.include_router(routes_precheck.router)
app.include_router(routes_eval.router)
app.include_router(routes_audit.router)
app.include_router(routes_batch.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
