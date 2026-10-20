"""Request and response shapes for the HTTP API."""

from pydantic import BaseModel, Field

from app.config import settings
from app.models.dish import Delta, Dish, UserDish
from app.models.vocab import Allergen


class ParseRepertoireRequest(BaseModel):
    """Free-text description of what the user cooks."""

    text: str = Field(..., min_length=3, max_length=settings.max_repertoire_text_chars)


class ParseRepertoireResponse(BaseModel):
    """The user's dishes, broken into parts."""

    dishes: list[UserDish]


class Diet(BaseModel):
    """Hard diet rules. Enforced in code — a dish that breaks one is never shown."""

    vegetarian: bool = False
    avoid: list[Allergen] = Field(default_factory=list, max_length=9)


class CousinsRequest(BaseModel):
    """The user's repertoire (as returned by parse) and how many cousins they want."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    limit: int = Field(default=settings.default_cousin_count, ge=1, le=settings.max_cousin_count)
    diet: Diet = Field(default_factory=Diet)


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


class TonightRequest(BaseModel):
    """What fits tonight: the user's kitchen, time available, diet, and picks to skip."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    max_minutes: int | None = Field(default=None, ge=10, le=480, description="None = any time")
    diet: Diet = Field(default_factory=Diet)
    skip: list[str] = Field(
        default_factory=list,
        max_length=settings.max_skip_ids,
        description="Catalog ids or the user's dish names they said 'not tonight' to",
    )


class TonightResponse(BaseModel):
    """Three ways to go tonight. Any of them may be missing if nothing fits."""

    familiar: UserDish | None = Field(None, description="One of the user's own dishes")
    one_step: Cousin | None = Field(None, description="A close new dish")
    stretch: Cousin | None = Field(None, description="A bigger leap, no new equipment")
