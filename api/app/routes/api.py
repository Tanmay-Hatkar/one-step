"""HTTP routes. Thin: validate, call a service, translate errors to status codes."""

import logging
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError

from app.config import settings
from app.deps import (
    get_cousin_service,
    get_dish_page_service,
    get_dish_repository,
    get_eval_repository,
    get_question_service,
    get_recipe_import_service,
    get_recipe_repository,
    get_repertoire_service,
    get_share_service,
    get_speech_service,
    get_technique_repository,
)
from app.limiter import limiter
from app.llm.client import LLMError
from app.models.api import (
    Cousin,
    CousinRequest,
    CousinsRequest,
    CousinsResponse,
    DishIndexEntry,
    DishPageResponse,
    MapRequest,
    MapResponse,
    ParseRepertoireRequest,
    ParseRepertoireResponse,
    PasteRequest,
    PasteResponse,
    PhotoKitchen,
    QuestionsRequest,
    QuestionsResponse,
    SharedKitchenResponse,
    ShareRequest,
    ShareResponse,
    TonightRequest,
    TonightResponse,
    TranscribeResponse,
)
from app.models.technique import TechniqueGuide
from app.repositories.dish_repository import DishRepository
from app.repositories.eval_repository import EvalResultsRepository
from app.repositories.page_repository import LinkNotSupported, PageUnreadable
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.share_repository import ShareStoreError
from app.repositories.technique_repository import TechniqueRepository
from app.services.cousin_service import CousinService
from app.services.dish_page_service import DishPageService
from app.services.llm_gateway import DailyCapExceeded
from app.services.question_service import QuestionService
from app.services.recipe_import_service import NotARecipe, PhotoRejected, RecipeImportService
from app.services.repertoire_service import NoDishesFound, RepertoireService
from app.services.share_service import ShareService
from app.services.speech_service import AudioRejected, NothingHeard, SpeechService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

BUSY_MESSAGE = "One Step is resting for today — too many people cooking. Try again tomorrow."
LLM_DOWN_MESSAGE = "Couldn't reach the kitchen brain just now. Please try again."
NOTHING_HEARD_MESSAGE = "I didn't catch any words. Try again a little closer to the mic."
BAD_AUDIO_MESSAGE = "That recording didn't work. Try again, or type it instead."
NOT_A_RECIPE_MESSAGE = "I couldn't find a recipe in that. Paste the ingredients and steps."
PAGE_UNREADABLE_MESSAGE = "I couldn't open that link. Copy the recipe text and paste it instead."
LINK_NOT_SUPPORTED_MESSAGE = (
    "I can't open links from that site yet. Copy the caption or recipe text and paste it here."
)
BAD_PHOTO_MESSAGE = "That picture didn't work. Try a screenshot or a clear photo of the recipe."
NO_RECIPE_IN_PHOTO_MESSAGE = (
    "I couldn't read a recipe in that picture. Make sure the ingredients are in the shot."
)
SHARE_DOWN_MESSAGE = "Couldn't save or open shared kitchens just now. Please try again."


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


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit(settings.voice_rate_limit)
async def transcribe(
    request: Request,
    audio: Annotated[UploadFile, File()],
    service: SpeechService = Depends(get_speech_service),
) -> TranscribeResponse:
    """Voice input: turn a short recording into text for the repertoire box."""
    try:
        # Read one byte past the limit so an oversized clip is rejected without buffering it all.
        clip = await audio.read(settings.max_audio_bytes + 1)
        text = await service.transcribe(clip, audio.content_type)
    except AudioRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, BAD_AUDIO_MESSAGE) from exc
    except NothingHeard as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, NOTHING_HEARD_MESSAGE) from exc
    except DailyCapExceeded as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, BUSY_MESSAGE) from exc
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, LLM_DOWN_MESSAGE) from exc
    return TranscribeResponse(text=text)


@router.post("/questions", response_model=QuestionsResponse)
@limiter.limit(settings.rate_limit)
async def questions(
    request: Request,
    body: QuestionsRequest,
    service: QuestionService = Depends(get_question_service),
) -> QuestionsResponse:
    """A few quick questions whose answers would change the suggestions. No LLM calls."""
    asked = service.ask(body.repertoire, body.diet, body.have, set(body.dismissed))
    return QuestionsResponse(questions=asked)


@router.post("/cousins", response_model=CousinsResponse)
@limiter.limit(settings.rate_limit)
async def cousins(
    request: Request,
    body: CousinsRequest,
    service: CousinService = Depends(get_cousin_service),
) -> CousinsResponse:
    """Dishes one step away from the user's repertoire, each written as a diff."""
    found = await service.find(body.repertoire, body.limit, body.diet, body.have)
    return CousinsResponse(cousins=found)


@router.post("/tonight", response_model=TonightResponse)
@limiter.limit(settings.rate_limit)
async def tonight(
    request: Request,
    body: TonightRequest,
    service: CousinService = Depends(get_cousin_service),
) -> TonightResponse:
    """A familiar dish, a one-step dish and a stretch that fit tonight's time and diet."""
    return await service.tonight(
        body.repertoire, body.diet, body.max_minutes, body.skip, body.have, body.recent
    )


@router.post("/map", response_model=MapResponse)
@limiter.limit(settings.rate_limit)
async def kitchen_map(
    request: Request,
    body: MapRequest,
    service: CousinService = Depends(get_cousin_service),
) -> MapResponse:
    """Your dishes with their closest cousins, for the map. No LLM calls."""
    return service.map(body.repertoire, body.diet, body.have)


@router.post("/cousin", response_model=Cousin)
@limiter.limit(settings.rate_limit)
async def one_cousin(
    request: Request,
    body: CousinRequest,
    service: CousinService = Depends(get_cousin_service),
) -> Cousin:
    """One dish written as a diff from your kitchen (a tap on the map)."""
    cousin = await service.one(body.repertoire, body.dish_id, body.diet, body.have)
    if cousin is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That dish isn't available for you.")
    return cousin


@router.post("/paste", response_model=PasteResponse)
@limiter.limit(settings.paste_rate_limit)
async def paste_recipe(
    request: Request,
    body: PasteRequest,
    service: RecipeImportService = Depends(get_recipe_import_service),
) -> PasteResponse:
    """A recipe from anywhere (link or text), written as a step from the user's kitchen."""
    try:
        return await service.paste(body.text, body.repertoire, body.diet, body.have)
    except LinkNotSupported as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, LINK_NOT_SUPPORTED_MESSAGE
        ) from exc
    except PageUnreadable as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, PAGE_UNREADABLE_MESSAGE) from exc
    except NotARecipe as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, NOT_A_RECIPE_MESSAGE) from exc
    except DailyCapExceeded as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, BUSY_MESSAGE) from exc
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, LLM_DOWN_MESSAGE) from exc


@router.post("/paste/photo", response_model=PasteResponse)
@limiter.limit(settings.photo_rate_limit)
async def paste_photo(
    request: Request,
    photo: Annotated[UploadFile, File()],
    kitchen: Annotated[str, Form(max_length=settings.max_synced_kitchen_bytes)],
    service: RecipeImportService = Depends(get_recipe_import_service),
) -> PasteResponse:
    """A screenshot or photo of a recipe, written as a step from the user's kitchen."""
    try:
        who = PhotoKitchen.model_validate_json(kitchen)
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Tell me a dish you cook first."
        ) from exc
    try:
        # One byte past the limit, so an oversized picture is rejected without buffering it.
        data = await photo.read(settings.max_photo_bytes + 1)
        return await service.paste_photo(data, who.repertoire, who.diet, who.have)
    except PhotoRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, BAD_PHOTO_MESSAGE) from exc
    except NotARecipe as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, NO_RECIPE_IN_PHOTO_MESSAGE
        ) from exc
    except DailyCapExceeded as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, BUSY_MESSAGE) from exc
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, LLM_DOWN_MESSAGE) from exc


@router.post("/shares", response_model=ShareResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.share_rate_limit)
async def create_share(
    request: Request,
    body: ShareRequest,
    service: ShareService = Depends(get_share_service),
) -> ShareResponse:
    """Save a read-only snapshot of a kitchen and return its id."""
    try:
        return ShareResponse(id=service.create(body.dishes))
    except ShareStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, SHARE_DOWN_MESSAGE) from exc


@router.get("/shares/{share_id}", response_model=SharedKitchenResponse)
async def get_share(
    share_id: str = Path(..., pattern=r"^[A-Za-z0-9_-]{4,16}$"),
    service: ShareService = Depends(get_share_service),
) -> SharedKitchenResponse:
    """Open a shared kitchen."""
    try:
        shared = service.get(share_id)
    except ShareStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, SHARE_DOWN_MESSAGE) from exc
    if shared is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That shared kitchen doesn't exist.")
    return shared


@router.get("/techniques", response_model=list[TechniqueGuide])
async def techniques(
    repo: TechniqueRepository = Depends(get_technique_repository),
) -> list[TechniqueGuide]:
    """How-to cards for every technique (static; cache freely)."""
    return repo.all()


@router.get("/evals")
async def eval_results(
    repo: EvalResultsRepository = Depends(get_eval_repository),
) -> dict[str, Any]:
    """The latest live eval results, for the public eval page."""
    results = repo.latest()
    if results is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No eval results yet.")
    return results


@router.get("/dishes/stats")
async def dish_stats(repo: DishRepository = Depends(get_dish_repository)) -> dict[str, int]:
    """How many dishes and regions are in the catalog (for the landing page)."""
    dishes = repo.all()
    return {"dishes": len(dishes), "regions": len({d.region for d in dishes})}


@router.get("/recipes", response_model=list[str])
async def recipe_ids(repo: RecipeRepository = Depends(get_recipe_repository)) -> list[str]:
    """Ids of dishes that have a full recipe (static; cache freely)."""
    return repo.ids()


@router.get("/dishes", response_model=list[DishIndexEntry])
async def dish_index(
    pages: DishPageService = Depends(get_dish_page_service),
) -> list[DishIndexEntry]:
    """Every catalog dish (static; cache freely). Feeds the sitemap and dish directory."""
    return pages.index()


@router.get("/dishes/{dish_id}", response_model=DishPageResponse)
async def dish_page(
    dish_id: str = Path(..., pattern=r"^[a-z0-9_]+$", max_length=60),
    pages: DishPageService = Depends(get_dish_page_service),
) -> DishPageResponse:
    """One catalog dish with its recipe and the dishes one step from it."""
    page = pages.page(dish_id)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We don't know that dish.")
    return page
