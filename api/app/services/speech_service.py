"""Turn a spoken description of someone's cooking into text for the repertoire box."""

import logging

from app.llm.transcriber import Transcriber
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

# Browser recording formats → the file extension the transcription API expects.
AUDIO_EXTENSIONS: dict[str, str] = {
    "audio/webm": "webm",
    "video/webm": "webm",  # some browsers label audio-only webm this way
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
    "audio/aac": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


class AudioRejected(ValueError):
    """The upload isn't a clip we can transcribe (wrong format, empty or too big)."""


class NothingHeard(ValueError):
    """The clip was fine but had no words in it."""


class SpeechService:
    """Validates a clip in code, then transcribes it within the shared daily budget."""

    def __init__(
        self,
        transcriber: Transcriber,
        gateway: LLMGateway,
        *,
        min_bytes: int,
        max_bytes: int,
        max_chars: int,
    ) -> None:
        """Args: transcriber, gateway (for the daily cap), clip size bounds, max_chars of text."""
        self._transcriber = transcriber
        self._gateway = gateway
        self._min_bytes = min_bytes
        self._max_bytes = max_bytes
        self._max_chars = max_chars

    async def transcribe(self, audio: bytes, content_type: str | None) -> str:
        """Transcribe one clip.

        Args:
            audio: The recorded clip.
            content_type: Its MIME type, e.g. 'audio/webm;codecs=opus'.

        Returns:
            What was said, trimmed to fit the repertoire box.

        Raises:
            AudioRejected: Unknown format, too short or too long.
            NothingHeard: No words in the clip.
            DailyCapExceeded: Today's budget is spent.
            LLMError: The transcription call failed.
        """
        extension = self._extension(content_type)
        if len(audio) < self._min_bytes:
            raise AudioRejected("Clip is empty")
        if len(audio) > self._max_bytes:
            raise AudioRejected("Clip is too long")

        self._gateway.check_cap()
        text = await self._transcriber.transcribe(audio, f"clip.{extension}")
        self._gateway.record_call()

        text = " ".join(text.split())[: self._max_chars]
        if not text:
            raise NothingHeard()
        logger.info("Transcribed %d bytes of %s into %d chars", len(audio), extension, len(text))
        return text

    @staticmethod
    def _extension(content_type: str | None) -> str:
        """'audio/webm;codecs=opus' → 'webm'."""
        base = (content_type or "").split(";")[0].strip().lower()
        if base not in AUDIO_EXTENSIONS:
            raise AudioRejected(f"Unsupported audio type: {base or 'none'}")
        return AUDIO_EXTENSIONS[base]
