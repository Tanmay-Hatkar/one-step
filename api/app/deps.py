"""Dependency providers. Built once per process; tests override them via FastAPI."""

from functools import lru_cache

from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import init_db, make_engine, make_session_factory
from app.llm.client import OpenAILLMClient
from app.llm.transcriber import OpenAITranscriber
from app.repositories.dish_repository import DishRepository
from app.repositories.eval_repository import EvalResultsRepository
from app.repositories.llm_repository import LLMCacheRepository, LLMUsageRepository
from app.repositories.share_repository import ShareRepository
from app.services.cousin_service import CousinService
from app.services.graph_service import GraphService
from app.services.llm_gateway import LLMGateway
from app.services.question_service import QuestionService
from app.services.repertoire_service import RepertoireService
from app.services.share_service import ShareService
from app.services.speech_service import SpeechService


@lru_cache
def get_session_factory() -> sessionmaker:
    """Engine + tables + session factory, created on first use."""
    engine = make_engine(settings.database_url)
    init_db(engine)
    return make_session_factory(engine)


@lru_cache
def get_dish_repository() -> DishRepository:
    """The in-memory dish catalog."""
    return DishRepository(settings.dishes_path)


@lru_cache
def get_gateway() -> LLMGateway:
    """The cached, capped LLM gateway."""
    sessions = get_session_factory()
    client = OpenAILLMClient(
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        reasoning_effort=settings.llm_reasoning_effort,
        timeout=settings.llm_timeout_seconds,
    )
    return LLMGateway(
        client,
        LLMCacheRepository(sessions),
        LLMUsageRepository(sessions),
        settings.daily_llm_call_cap,
    )


def get_repertoire_service() -> RepertoireService:
    """Repertoire parsing service."""
    return RepertoireService(get_gateway(), get_dish_repository(), settings.max_repertoire_dishes)


def get_cousin_service() -> CousinService:
    """Cousin search + diff writing service."""
    graph = GraphService(get_dish_repository().all(), settings)
    return CousinService(graph, get_gateway())


def get_question_service() -> QuestionService:
    """Follow-up questions (no LLM)."""
    return QuestionService(GraphService(get_dish_repository().all(), settings), settings)


@lru_cache
def get_eval_repository() -> EvalResultsRepository:
    """The latest eval results, loaded once."""
    return EvalResultsRepository(settings.eval_results_path)


def get_share_service() -> ShareService:
    """Shared kitchen snapshots."""
    return ShareService(ShareRepository(get_session_factory(), settings.share_id_bytes))


@lru_cache
def get_speech_service() -> SpeechService:
    """Voice input: speech-to-text within the shared daily budget."""
    transcriber = OpenAITranscriber(
        api_key=settings.openai_api_key,
        model=settings.transcribe_model,
        timeout=settings.llm_timeout_seconds,
    )
    return SpeechService(
        transcriber,
        get_gateway(),
        min_bytes=settings.min_audio_bytes,
        max_bytes=settings.max_audio_bytes,
        max_chars=settings.max_repertoire_text_chars,
    )
