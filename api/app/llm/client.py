"""LLM client abstraction. Services depend on the protocol, never on OpenAI directly."""

import logging
import time
from dataclasses import dataclass
from typing import Protocol, TypeVar

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The LLM call failed or returned nothing usable."""


class LLMClient(Protocol):
    """Anything that can turn a prompt into a validated Pydantic object."""

    model: str

    async def parse(self, *, instructions: str, prompt: str, schema: type[T]) -> T:
        """Return `schema` filled from the model's structured output."""
        ...


@dataclass
class Usage:
    """Running totals for real (uncached) calls, for cost and latency reports."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


class OpenAILLMClient:
    """OpenAI Responses API with strict structured outputs."""

    def __init__(self, api_key: str, model: str, reasoning_effort: str, timeout: float) -> None:
        """Args: api_key, model, reasoning_effort ('low'|'medium'|'high', or '' for
        non-reasoning models like gpt-4.1-mini), timeout seconds."""
        self.model = model
        self._effort = reasoning_effort
        self.usage = Usage()
        # No key → no client; calls fail with a clean LLMError instead of crashing the app.
        self._client = (
            AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=1) if api_key else None
        )

    async def parse(self, *, instructions: str, prompt: str, schema: type[T]) -> T:
        """Call the model and validate its output.

        Args:
            instructions: System-level instructions.
            prompt: The user-level input.
            schema: Pydantic model the output must match.

        Returns:
            A validated instance of `schema`.

        Raises:
            LLMError: On API failure or empty/refused output.
        """
        if self._client is None:
            raise LLMError("OPENAI_API_KEY is not configured")
        extra = {"reasoning": {"effort": self._effort}} if self._effort else {}
        started = time.perf_counter()
        try:
            response = await self._client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=prompt,
                text_format=schema,
                **extra,
            )
        except OpenAIError as exc:
            logger.warning("OpenAI call failed: %s", exc)
            raise LLMError(str(exc)) from exc
        self.usage.calls += 1
        self.usage.seconds += time.perf_counter() - started
        if response.usage:
            self.usage.input_tokens += response.usage.input_tokens
            self.usage.output_tokens += response.usage.output_tokens
        parsed = response.output_parsed
        if parsed is None:
            raise LLMError("Model returned no structured output")
        return parsed
