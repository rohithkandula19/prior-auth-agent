"""Use Claude to convert parsed policy text into structured Criterion objects.

Verbatim preservation is critical: criterion.text must be a substring of the
parsed raw_text. We verify that and re-derive char_span from the substring
position rather than trusting the model to count characters.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger
from app.ingestion.policy_parser import ParsedPolicy
from app.schemas.policy import Criterion

log = get_logger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "agent" / "prompts" / "criteria_extraction.txt"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _locate_span(haystack: str, needle: str) -> tuple[int, int] | None:
    """Find needle in haystack. Tolerates collapsed whitespace."""
    idx = haystack.find(needle)
    if idx >= 0:
        return (idx, idx + len(needle))

    # Loose match: collapse whitespace on both sides and search.
    import re

    norm_needle = re.sub(r"\s+", " ", needle).strip()
    if not norm_needle:
        return None

    # Build a regex that allows any whitespace between tokens.
    pattern = re.compile(
        r"\s+".join(re.escape(tok) for tok in norm_needle.split(" ")),
        re.DOTALL,
    )
    match = pattern.search(haystack)
    if match:
        return (match.start(), match.end())
    return None


class CriteriaExtractor:
    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or get_client()
        self.prompt_template = _load_prompt()

    def extract(self, parsed: ParsedPolicy) -> tuple[list[Criterion], dict]:
        prompt = self.prompt_template.format(policy_text=parsed.raw_text)
        resp = self.client.complete(prompt, max_tokens=8192, temperature=0.0)

        try:
            raw = resp.parse_json()
        except Exception as exc:
            log.error("criteria_json_parse_failed", error=str(exc), text_head=resp.text[:400])
            raise

        if not isinstance(raw, list):
            raise ValueError(f"Expected JSON array, got {type(raw).__name__}")

        criteria: list[Criterion] = []
        warnings: list[str] = []
        for entry in raw:
            text = (entry.get("text") or "").strip()
            span = _locate_span(parsed.raw_text, text)
            if span is None:
                warnings.append(f"non-verbatim criterion {entry.get('id')!r}: {text[:80]}")
                # Fall back to (0, 0) but keep the criterion so reviewers can see what was emitted.
                span = (0, 0)
            try:
                crit = Criterion(
                    id=entry["id"],
                    text=text,
                    type=entry.get("type", "required"),
                    parent_id=entry.get("parent_id"),
                    page_number=int(entry.get("page_number", 1)),
                    char_span=span,
                )
            except (KeyError, ValidationError) as exc:
                warnings.append(f"invalid criterion entry {entry!r}: {exc}")
                continue
            criteria.append(crit)

        meta = {
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
            "latency_ms": resp.latency_ms,
            "warnings": warnings,
            "criterion_count": len(criteria),
        }
        log.info("criteria_extracted", **meta)
        return criteria, meta
