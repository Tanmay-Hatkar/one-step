"""Every LLM call goes through here: cache first, then the daily cap, then the model."""

import hashlib
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.llm.client import Image, LLMClient
from app.repositories.llm_repository import LLMCacheRepository, LLMUsageRepository

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class DailyCapExceeded(RuntimeError):
    """Today's LLM call budget is used up."""


class LLMGateway:
    """Caches identical requests and enforces a per-day call cap (cost safety)."""

    def __init__(
        self,
        client: LLMClient,
        cache: LLMCacheRepository,
        usage: LLMUsageRepository,
        daily_cap: int,
    ) -> None:
        """Args: client, cache repo, usage repo, daily_cap (max real calls per UTC day)."""
        self._client = client
        self._cache = cache
        self._usage = usage
        self._daily_cap = daily_cap

    async def run(
        self,
        *,
        task: str,
        instructions: str,
        prompt: str,
        schema: type[T],
        image: Image | None = None,
    ) -> T:
        """Return a cached or fresh structured response.

        Args:
            task: Short label for logs and the cache ('parse_repertoire', 'write_diff').
            instructions: System instructions.
            prompt: User-level input.
            schema: Output model.
            image: Optional picture for the model to read; part of the cache key.

        Returns:
            A validated `schema` instance.

        Raises:
            DailyCapExceeded: If today's budget is spent (or usage can't be read).
            LLMError: If the model call fails.
        """
        key = self._key(task, instructions, prompt, image)
        cached = self._cache.get(key)
        if cached is not None:
            try:
                return schema.model_validate_json(cached)
            except ValidationError:
                logger.warning("Stale cache entry for %s; refreshing", task)

        self.check_cap()
        result = await self._client.parse(
            instructions=instructions, prompt=prompt, schema=schema, image=image
        )
        self.record_call()
        self._usage.record_tokens(*getattr(self._client, "last_tokens", (0, 0)))
        self._cache.put(key, task, self._client.model, result.model_dump_json())
        return result

    def check_cap(self) -> None:
        """Raise DailyCapExceeded if today's budget is spent.

        Fails closed: if usage can't be read, don't spend.

        Public so other paid calls (speech-to-text) share the same daily budget.
        """
        try:
            calls = self._usage.calls_today()
        except SQLAlchemyError as exc:
            logger.exception("Usage read failed; refusing LLM call")
            raise DailyCapExceeded("Usage tracking unavailable") from exc
        if calls >= self._daily_cap:
            logger.warning("Daily LLM cap reached (%d)", self._daily_cap)
            raise DailyCapExceeded(f"Daily limit of {self._daily_cap} calls reached")

    def record_call(self) -> None:
        """Count one paid call against today's budget."""
        self._usage.record_call()

    def _key(self, task: str, instructions: str, prompt: str, image: Image | None = None) -> str:
        """Stable cache key over everything that affects the output."""
        picture = hashlib.sha256(image.data).hexdigest() if image else ""
        material = "\x1f".join([self._client.model, task, instructions, prompt, picture])
        return hashlib.sha256(material.encode()).hexdigest()
