"""Voice input: clip validation in code, the shared daily cap, and the HTTP route."""

import pytest
from fastapi.testclient import TestClient

from app.deps import get_speech_service
from app.llm.client import LLMError
from app.main import create_app
from app.services.llm_gateway import DailyCapExceeded
from app.services.speech_service import AudioRejected, NothingHeard, SpeechService
from tests.conftest import FakeLLMClient

CLIP = b"\x1a\x45\xdf\xa3" + b"\x00" * 4_000  # webm magic + padding; content isn't inspected


class FakeTranscriber:
    model = "fake-transcribe"

    def __init__(self, text: str = "I make dal tadka and jeera rice", fail: bool = False) -> None:
        self.text, self.fail = text, fail
        self.filenames: list[str] = []

    async def transcribe(self, audio: bytes, filename: str) -> str:
        self.filenames.append(filename)
        if self.fail:
            raise LLMError("boom")
        return self.text


def make_service(make_gateway, transcriber=None, cap: int = 100, max_chars: int = 1500):
    gateway = make_gateway(FakeLLMClient(lambda schema, prompt: None), cap=cap)
    return SpeechService(
        transcriber or FakeTranscriber(),
        gateway,
        min_bytes=1_000,
        max_bytes=10_000,
        max_chars=max_chars,
    )


async def test_transcribes_and_names_file_by_format(make_gateway) -> None:
    transcriber = FakeTranscriber()
    service = make_service(make_gateway, transcriber)
    assert await service.transcribe(CLIP, "audio/webm;codecs=opus") == (
        "I make dal tadka and jeera rice"
    )
    await service.transcribe(CLIP, "audio/mp4")
    assert transcriber.filenames == ["clip.webm", "clip.mp4"]


async def test_tidies_and_trims_text(make_gateway) -> None:
    service = make_service(make_gateway, FakeTranscriber("  dal \n\n and   rice "), max_chars=7)
    assert await service.transcribe(CLIP, "audio/webm") == "dal and"


@pytest.mark.parametrize(
    ("clip", "content_type"),
    [
        (CLIP, "text/plain"),
        (CLIP, None),
        (b"\x00" * 10, "audio/webm"),
        (b"\x00" * 20_000, "audio/webm"),
    ],
)
async def test_rejects_bad_clips_without_spending(make_gateway, clip, content_type) -> None:
    transcriber = FakeTranscriber()
    service = make_service(make_gateway, transcriber)
    with pytest.raises(AudioRejected):
        await service.transcribe(clip, content_type)
    assert transcriber.filenames == []


async def test_silence_is_nothing_heard(make_gateway) -> None:
    with pytest.raises(NothingHeard):
        await make_service(make_gateway, FakeTranscriber("   ")).transcribe(CLIP, "audio/webm")


async def test_shares_daily_cap(make_gateway) -> None:
    transcriber = FakeTranscriber()
    service = make_service(make_gateway, transcriber, cap=1)
    await service.transcribe(CLIP, "audio/webm")
    with pytest.raises(DailyCapExceeded):
        await service.transcribe(CLIP, "audio/webm")
    assert len(transcriber.filenames) == 1


class StubSpeech:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text, self.error = text, error

    async def transcribe(self, audio: bytes, content_type: str | None) -> str:
        if self.error:
            raise self.error
        return self.text


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        test_client.app_ref = app  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()


def post_clip(client: TestClient):
    return client.post(
        "/api/transcribe", files={"audio": ("clip.webm", CLIP, "audio/webm;codecs=opus")}
    )


def test_route_ok(client) -> None:
    client.app_ref.dependency_overrides[get_speech_service] = lambda: StubSpeech("dal and rice")
    response = post_clip(client)
    assert response.status_code == 200
    assert response.json() == {"text": "dal and rice"}


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (AudioRejected(), 422),
        (NothingHeard(), 422),
        (DailyCapExceeded(), 503),
        (LLMError(), 502),
    ],
)
def test_route_errors_map_to_status(client, error, status) -> None:
    client.app_ref.dependency_overrides[get_speech_service] = lambda: StubSpeech(error=error)
    response = post_clip(client)
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)


def test_route_requires_a_file(client) -> None:
    client.app_ref.dependency_overrides[get_speech_service] = lambda: StubSpeech("x")
    assert client.post("/api/transcribe").status_code == 422
