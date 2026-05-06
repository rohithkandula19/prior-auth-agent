"""Anthropic Claude client wrapper with cost tracking and JSON parsing helpers."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Approximate published Sonnet 4.5 prices, USD per million tokens.
# Update if pricing changes; used only for eval cost estimates.
INPUT_PRICE_PER_MTOK = 3.0
OUTPUT_PRICE_PER_MTOK = 15.0


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int

    def parse_json(self) -> Any:
        """Extract JSON from the response text. Tolerates fenced code blocks."""
        cleaned = _strip_code_fence(self.text)
        return json.loads(cleaned)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


class ClaudeClient:
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.anthropic_model
        self._client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        start = time.monotonic()
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        in_tok = message.usage.input_tokens
        out_tok = message.usage.output_tokens
        cost = (in_tok / 1_000_000) * INPUT_PRICE_PER_MTOK + (
            out_tok / 1_000_000
        ) * OUTPUT_PRICE_PER_MTOK

        log.debug(
            "claude_complete",
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
        )
        return LLMResponse(
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=cost,
            latency_ms=latency_ms,
        )


def get_client() -> ClaudeClient:
    return ClaudeClient()
