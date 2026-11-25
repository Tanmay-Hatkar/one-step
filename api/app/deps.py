"""Dependency providers. Built once per process; tests override them via FastAPI."""

from functools import lru_cache

from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import init_db, make_engine, make_session_factory
from app.llm.client import OpenAILLMClient
from app.llm.transcriber import OpenAITranscriber
from app.repositories.account_repository import AccountRepository
from app.repositories.dish_repository import DishRepository
from app.repositories.eval_repository import EvalResultsRepository
from app.repositories.insight_repository import InsightRepository
from app.repositories.llm_repository import LLMCacheRepository, LLMUsageRepository
from app.repositories.page_repository import PageRepository
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.share_repository import ShareRepository
from app.repositories.substitution_repository import SubstitutionRepository
from app.repositories.technique_repository import TechniqueRepository
from app.services.account_service import AccountService
from app.services.cousin_service import CousinService
from app.services.dish_page_service import DishPageService
from app.services.graph_service import GraphService
from app.services.insight_service import InsightService
from app.services.llm_gateway import LLMGateway
from app.services.question_service import QuestionService
from app.services.recipe_import_service import RecipeImportService
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


@lru_cache
def get_substitution_repository() -> SubstitutionRepository:
    """Ingredient stand-ins, loaded once."""
    return SubstitutionRepository(settings.substitutions_path)


@lru_cache
def get_recipe_repository() -> RecipeRepository:
    """Full recipes (Wikibooks Cookbook, CC BY-SA), loaded once."""
    return RecipeRepository(settings.recipes_path)


@lru_cache
def get_technique_repository() -> TechniqueRepository:
    """Technique how-to cards, loaded once."""
    return TechniqueRepository(settings.techniques_path)


@lru_cache
def get_graph() -> GraphService:
    """The dish graph with substitutions. Stateless after construction, so shared."""
    return GraphService(
        get_dish_repository().all(),
        settings,
        substitutes=get_substitution_repository().usable(),
    )


def get_repertoire_service() -> RepertoireService:
    """Repertoire parsing service."""
    return RepertoireService(get_gateway(), get_dish_repository(), settings.max_repertoire_dishes)


def get_cousin_service() -> CousinService:
    """Cousin search + diff writing service."""
    return CousinService(get_graph(), get_gateway())


@lru_cache
def get_page_repository() -> PageRepository:
    """Reader for pasted recipe links (public pages only)."""
    return PageRepository(
        timeout=settings.page_timeout_seconds,
        max_bytes=settings.max_page_bytes,
        max_redirects=settings.max_page_redirects,
        user_agent=settings.page_user_agent,
        unreadable_hosts=settings.unreadable_host_list,
    )


def get_recipe_import_service() -> RecipeImportService:
    """Paste a recipe: read it, then write it up from the user's kitchen."""
    return RecipeImportService(
        get_gateway(),
        get_graph(),
        get_cousin_service(),
        get_page_repository(),
        max_chars=settings.max_paste_chars,
        link_note_max_chars=settings.link_note_max_chars,
        max_photo_bytes=settings.max_photo_bytes,
    )


def get_question_service() -> QuestionService:
    """Follow-up questions (no LLM)."""
    return QuestionService(get_graph(), settings)


@lru_cache
def get_eval_repository() -> EvalResultsRepository:
    """The latest eval results, loaded once."""
    return EvalResultsRepository(settings.eval_results_path)


def get_account_service() -> AccountService:
    """Optional passkey accounts and the synced kitchen."""
    return AccountService(AccountRepository(get_session_factory()), settings)


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


@lru_cache
def get_insight_service() -> InsightService:
    """Feedback and anonymous usage stats."""
    return InsightService(InsightRepository(get_session_factory()))


@lru_cache
def get_dish_page_service() -> DishPageService:
    """The public dish-page builder (catalog + recipes + graph)."""
    return DishPageService(get_dish_repository(), get_recipe_repository(), get_graph(), settings)
