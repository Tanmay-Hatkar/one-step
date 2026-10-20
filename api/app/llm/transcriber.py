"""Speech-to-text client. Services depend on the protocol, never on OpenAI directly."""

import logging
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError

from app.llm.client import LLMError

logger = logging.getLogger(__name__)

# Spelling hints for words a general model often mishears in a kitchen.
COOKING_HINT = (
    "A home cook describing dishes they make, e.g. dal tadka, jeera rice, biryani, paneer, "
    "garam masala, ghee, roti, sambar, rasam, poha, adobo, pho, gochujang, shakshuka."
)


class Transcriber(Protocol):
    """Anything that can turn a short audio clip into text."""

    model: str

    async def transcribe(self, audio: bytes, filename: str) -> str:
        """Return what was said in `audio`."""
        ...


class OpenAITranscriber:
    """OpenAI audio transcriptions."""

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        """Args: api_key, model (e.g. 'gpt-4o-mini-transcribe'), timeout seconds."""
        self.model = model
        self._client = (
            AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=1) if api_key else None
        )

    async def transcribe(self, audio: bytes, filename: str) -> str:
        """Transcribe one clip.

        Args:
            audio: Encoded audio (webm, mp4, ogg, wav, mp3...).
            filename: Name with an extension matching the encoding; the API reads it.

        Returns:
            The transcript (may be empty if nothing was said).

        Raises:
            LLMError: On API failure.
        """
        if self._client is None:
            raise LLMError("OPENAI_API_KEY is not configured")
        try:
            result = await self._client.audio.transcriptions.create(
                model=self.model,
                file=(filename, audio),
                prompt=COOKING_HINT,
                response_format="text",
            )
        except OpenAIError as exc:
            logger.warning("Transcription failed: %s", exc)
            raise LLMError(str(exc)) from exc
        return result if isinstance(result, str) else getattr(result, "text", "")
