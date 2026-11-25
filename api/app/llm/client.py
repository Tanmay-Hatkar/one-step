"""LLM client abstraction. Services depend on the protocol, never on OpenAI directly."""

import base64
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


@dataclass(frozen=True)
class Image:
    """A picture for the model to read (a recipe screenshot or photo)."""

    data: bytes
    media_type: str  # e.g. "image/jpeg"

    def data_url(self) -> str:
        """The image as a base64 data URL."""
        return f"data:{self.media_type};base64,{base64.b64encode(self.data).decode()}"


class LLMClient(Protocol):
    """Anything that can turn a prompt into a validated Pydantic object."""

    model: str

    async def parse(
        self, *, instructions: str, prompt: str, schema: type[T], image: Image | None = None
    ) -> T:
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
        # Tokens of the most recent call; read right after `parse` returns (no await between).
        self.last_tokens: tuple[int, int] = (0, 0)
        # No key → no client; calls fail with a clean LLMError instead of crashing the app.
        self._client = (
            AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=1) if api_key else None
        )

    async def parse(
        self, *, instructions: str, prompt: str, schema: type[T], image: Image | None = None
    ) -> T:
        """Call the model and validate its output.

        Args:
            instructions: System-level instructions.
            prompt: The user-level input.
            schema: Pydantic model the output must match.
            image: Optional picture sent alongside the prompt.

        Returns:
            A validated instance of `schema`.

        Raises:
            LLMError: On API failure or empty/refused output.
        """
        if self._client is None:
            raise LLMError("OPENAI_API_KEY is not configured")
        extra = {"reasoning": {"effort": self._effort}} if self._effort else {}
        content: str | list = prompt
        if image is not None:
            parts = [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": image.data_url()},
            ]
            content = [{"role": "user", "content": parts}]
        started = time.perf_counter()
        try:
            response = await self._client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=content,
                text_format=schema,
                **extra,
            )
        except OpenAIError as exc:
            logger.warning("OpenAI call failed: %s", exc)
            raise LLMError(str(exc)) from exc
        self.usage.calls += 1
        self.usage.seconds += time.perf_counter() - started
        self.last_tokens = (0, 0)
        if response.usage:
            self.usage.input_tokens += response.usage.input_tokens
            self.usage.output_tokens += response.usage.output_tokens
            self.last_tokens = (response.usage.input_tokens, response.usage.output_tokens)
        parsed = response.output_parsed
        if parsed is None:
            raise LLMError("Model returned no structured output")
        return parsed
