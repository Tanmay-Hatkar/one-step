"""Request and response shapes for the HTTP API."""

from pydantic import BaseModel, Field

from app.config import settings
from app.models.dish import Delta, Dish, UserDish


class ParseRepertoireRequest(BaseModel):
    """Free-text description of what the user cooks."""

    text: str = Field(..., min_length=3, max_length=settings.max_repertoire_text_chars)


class ParseRepertoireResponse(BaseModel):
    """The user's dishes, broken into parts."""

    dishes: list[UserDish]


class CousinsRequest(BaseModel):
    """The user's repertoire (as returned by parse) and how many cousins they want."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_repertoire_dishes)
    limit: int = Field(default=settings.default_cousin_count, ge=1, le=settings.max_cousin_count)


class DiffText(BaseModel):
    """The written difference: 'Kabsa: your usual rice, but…' plus the changes."""

    headline: str = Field(..., max_length=120)
    changes: list[str] = Field(..., min_length=1, max_length=6)
    keep_line: str = Field(..., max_length=160)


class Cousin(BaseModel):
    """One suggested dish, the user dish it's closest to, and what's different."""

    dish: Dish
    delta: Delta
    diff: DiffText


class CousinsResponse(BaseModel):
    """Suggested cousins, closest first."""

    cousins: list[Cousin]
