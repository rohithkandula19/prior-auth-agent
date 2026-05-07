"""Eval endpoints. Thin wrapper over app.eval.harness."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.eval.compare import run_compare
from app.eval.harness import EvalRun, run_eval
from app.eval.metrics import latest_summary

router = APIRouter(prefix="/eval", tags=["eval"])


class EvalRunRequest(BaseModel):
    gold_set_path: str | None = None
    limit: int | None = None


@router.post("/run", response_model=EvalRun)
async def post_run(req: EvalRunRequest) -> EvalRun:
    return run_eval(gold_set_path=req.gold_set_path, limit=req.limit)


@router.get("/metrics")
async def get_metrics() -> dict:
    return latest_summary()


@router.get("/failure_modes")
async def get_failure_modes() -> dict:
    summary = latest_summary()
    return {"failure_modes": summary.get("failure_modes", {})}


class CompareRequest(BaseModel):
    models: list[str]
    limit: int | None = None


@router.post("/compare")
async def post_compare(req: CompareRequest) -> dict:
    return run_compare(req.models, limit=req.limit)
