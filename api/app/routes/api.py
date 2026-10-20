"""HTTP routes. Thin: validate, call a service, translate errors to status codes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.deps import get_cousin_service, get_dish_repository, get_repertoire_service
from app.limiter import limiter
from app.llm.client import LLMError
from app.models.api import (
    CousinsRequest,
    CousinsResponse,
    ParseRepertoireRequest,
    ParseRepertoireResponse,
    TonightRequest,
    TonightResponse,
)
from app.repositories.dish_repository import DishRepository
from app.services.cousin_service import CousinService
from app.services.llm_gateway import DailyCapExceeded
from app.services.repertoire_service import NoDishesFound, RepertoireService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

BUSY_MESSAGE = "One Step is resting for today — too many people cooking. Try again tomorrow."
LLM_DOWN_MESSAGE = "Couldn't reach the kitchen brain just now. Please try again."


@router.post("/repertoire/parse", response_model=ParseRepertoireResponse)
@limiter.limit(settings.rate_limit)
async def parse_repertoire(
    request: Request,
    body: ParseRepertoireRequest,
    service: RepertoireService = Depends(get_repertoire_service),
) -> ParseRepertoireResponse:
    """Turn 'what I usually cook' text into structured dishes."""
    try:
        dishes = await service.parse(body.text)
    except NoDishesFound as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Tell me about a dish or two you cook."
        ) from exc
    except DailyCapExceeded as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, BUSY_MESSAGE) from exc
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, LLM_DOWN_MESSAGE) from exc
    return ParseRepertoireResponse(dishes=dishes)


@router.post("/cousins", response_model=CousinsResponse)
@limiter.limit(settings.rate_limit)
async def cousins(
    request: Request,
    body: CousinsRequest,
    service: CousinService = Depends(get_cousin_service),
) -> CousinsResponse:
    """Dishes one step away from the user's repertoire, each written as a diff."""
    found = await service.find(body.repertoire, body.limit, body.diet)
    return CousinsResponse(cousins=found)


@router.post("/tonight", response_model=TonightResponse)
@limiter.limit(settings.rate_limit)
async def tonight(
    request: Request,
    body: TonightRequest,
    service: CousinService = Depends(get_cousin_service),
) -> TonightResponse:
    """A familiar dish, a one-step dish and a stretch that fit tonight's time and diet."""
    return await service.tonight(body.repertoire, body.diet, body.max_minutes, body.skip)


@router.get("/dishes/stats")
async def dish_stats(repo: DishRepository = Depends(get_dish_repository)) -> dict[str, int]:
    """How many dishes and regions are in the catalog (for the landing page)."""
    dishes = repo.all()
    return {"dishes": len(dishes), "regions": len({d.region for d in dishes})}
