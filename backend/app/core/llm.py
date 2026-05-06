"""LLM client wrapper. Dispatches between Anthropic and OpenRouter based on
settings.llm_provider so the rest of the codebase keeps a single interface.

Public type is still `ClaudeClient` so existing call sites and stub clients
in tests/scripts do not need to change. Subclasses override `complete`.
"""

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
# Used only for eval cost estimates; the OpenRouter path reports zero cost
# because OpenRouter does its own metering.
ANTHROPIC_INPUT_PRICE_PER_MTOK = 3.0
ANTHROPIC_OUTPUT_PRICE_PER_MTOK = 15.0


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int

    def parse_json(self) -> Any:
        cleaned = _strip_code_fence(self.text)
        return json.loads(cleaned)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


class ClaudeClient:
    """Default Anthropic-backed implementation. Subclasses override .complete."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.anthropic_model
        resolved_key = api_key or settings.anthropic_api_key or None
        self._client = anthropic.Anthropic(api_key=resolved_key)

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
        cost = (in_tok / 1_000_000) * ANTHROPIC_INPUT_PRICE_PER_MTOK + (
            out_tok / 1_000_000
        ) * ANTHROPIC_OUTPUT_PRICE_PER_MTOK
        log.debug(
            "anthropic_complete",
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
        )
        return LLMResponse(text, in_tok, out_tok, cost, latency_ms)


class OpenRouterClient(ClaudeClient):
    """OpenAI-compatible client pointing at OpenRouter."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        # Skip ClaudeClient.__init__ on purpose; we need a different SDK.
        from openai import OpenAI

        self.model = model or settings.openrouter_model
        resolved_key = api_key or settings.openrouter_api_key or None
        if not resolved_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        self._openai = OpenAI(
            api_key=resolved_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": settings.openrouter_referer,
                "X-Title": settings.openrouter_app_title,
            },
        )

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
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self._openai.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        choice = resp.choices[0]
        text = choice.message.content or ""

        usage = resp.usage
        in_tok = getattr(usage, "prompt_tokens", 0) or 0
        out_tok = getattr(usage, "completion_tokens", 0) or 0
        # OpenRouter has its own pricing; do not estimate here.
        cost = 0.0
        log.debug(
            "openrouter_complete",
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason,
        )
        return LLMResponse(text, in_tok, out_tok, cost, latency_ms)


def get_client() -> ClaudeClient:
    provider = (settings.llm_provider or "anthropic").lower()
    if provider == "openrouter":
        return OpenRouterClient()
    return ClaudeClient()
