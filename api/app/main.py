"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.deps import get_dish_repository, get_session_factory
from app.limiter import limiter
from app.routes.account import router as account_router
from app.routes.api import router

logging.basicConfig(
    level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Fail fast at startup if the catalog or database is broken."""
    get_dish_repository()
    get_session_factory()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set; LLM endpoints will fail")
    yield


def create_app() -> FastAPI:
    """Build the app: CORS, rate limiting, routes."""
    app = FastAPI(title="One Step API", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(router)
    app.include_router(account_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness check."""
        return {"status": "ok"}

    return app


app = create_app()
