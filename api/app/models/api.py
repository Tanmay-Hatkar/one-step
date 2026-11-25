"""Request and response shapes for the HTTP API."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.config import settings
from app.models.dish import Delta, Dish, UserDish
from app.models.recipe import Recipe
from app.models.vocab import Allergen, Equipment, Protein, Technique


class ParseRepertoireRequest(BaseModel):
    """Free-text description of what the user cooks."""

    text: str = Field(..., min_length=3, max_length=settings.max_repertoire_text_chars)


class ParseRepertoireResponse(BaseModel):
    """The user's dishes, broken into parts."""

    dishes: list[UserDish]


class TranscribeResponse(BaseModel):
    """What the user said, ready to drop into the repertoire box."""

    text: str


class Diet(BaseModel):
    """Hard diet rules. Enforced in code — a dish that breaks one is never shown."""

    vegetarian: bool = False
    avoid: list[Allergen] = Field(default_factory=list, max_length=9)


IngredientName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]


class Have(BaseModel):
    """What the user has beyond what their dishes imply: equipment and pantry items."""

    equipment: list[Equipment] = Field(default_factory=list, max_length=12)
    ingredients: list[IngredientName] = Field(
        default_factory=list, max_length=settings.max_pantry_items
    )


class CousinsRequest(BaseModel):
    """The user's repertoire (as returned by parse) and how many cousins they want."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    limit: int = Field(default=settings.default_cousin_count, ge=1, le=settings.max_cousin_count)
    diet: Diet = Field(default_factory=Diet)
    have: Have = Field(default_factory=Have)


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
    have: Have = Field(default_factory=Have)
    skip: list[str] = Field(
        default_factory=list,
        max_length=settings.max_skip_ids,
        description="Catalog ids or the user's dish names they said 'not tonight' to",
    )
    recent: list[str] = Field(
        default_factory=list,
        max_length=settings.max_recent_cooked,
        description="Names of the user's dishes they cooked lately, most recent first",
    )


class TonightResponse(BaseModel):
    """Three ways to go tonight. Any of them may be missing if nothing fits."""

    familiar: UserDish | None = Field(None, description="One of the user's own dishes")
    one_step: Cousin | None = Field(None, description="A close new dish")
    stretch: Cousin | None = Field(None, description="A bigger leap, no new equipment")
    reach: int = Field(0, description="Catalog dishes one step from the kitchen, under the diet")


class MapRequest(BaseModel):
    """The user's kitchen and diet; the map is drawn around it."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    diet: Diet = Field(default_factory=Diet)
    have: Have = Field(default_factory=Have)


class MapCousin(BaseModel):
    """A dish on the map: no written diff yet (that's fetched on tap)."""

    dish: Dish
    delta: Delta


class MapResponse(BaseModel):
    """Your dishes in the middle, their closest cousins around them."""

    kitchen: list[UserDish]
    cousins: list[MapCousin]
    one_step_count: int = Field(..., description="Catalog dishes one step from your kitchen")
    catalog_size: int


class CousinRequest(BaseModel):
    """Write up one specific dish relative to the user's kitchen (a tap on the map)."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    dish_id: str = Field(..., pattern=r"^[a-z0-9_]+$", max_length=60)
    diet: Diet = Field(default_factory=Diet)
    have: Have = Field(default_factory=Have)


class PasteRequest(BaseModel):
    """A recipe from anywhere (a link or its text) and the kitchen to rewrite it from."""

    text: str = Field(..., min_length=8, max_length=settings.max_paste_chars)
    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    diet: Diet = Field(default_factory=Diet)
    have: Have = Field(default_factory=Have)


class PhotoKitchen(BaseModel):
    """The kitchen sent alongside a recipe photo (as a JSON form field)."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    diet: Diet = Field(default_factory=Diet)
    have: Have = Field(default_factory=Have)


class PastedRecipe(BaseModel):
    """The recipe as read from the paste: kept on the user's device, never stored here."""

    ingredients: list[str]
    steps: list[str]
    source_url: str | None = Field(None, description="The link it came from, if it was a link")


class PasteResponse(BaseModel):
    """A pasted recipe as a step from the user's kitchen."""

    cousin: Cousin
    recipe: PastedRecipe
    breaks_diet: list[str] = Field(
        default_factory=list,
        description="Diet rules it breaks, worked out in code: allergen ids and/or 'vegetarian'",
    )


class ShareRequest(BaseModel):
    """A kitchen to share: the user's dishes, as they appear in the app."""

    dishes: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)


class ShareResponse(BaseModel):
    """The new share id; the web app turns it into a /k/<id> link."""

    id: str


class SharedKitchenResponse(BaseModel):
    """A shared kitchen, read-only."""

    dishes: list[UserDish]
    created_at: str


class Patch(BaseModel):
    """What an answer changes. Applied by the client; re-validated on the next request."""

    dish: int | None = Field(None, ge=0, description="Index into the repertoire; None = kitchen")
    add_techniques: list[Technique] = Field(default_factory=list)
    protein: Protein | None = None
    add_equipment: list[Equipment] = Field(
        default_factory=list, description="Kitchen-level: goes into Have"
    )


class QuestionOption(BaseModel):
    """One tappable answer."""

    label: str
    patch: Patch


class Question(BaseModel):
    """A quick question whose answer would change the suggestions."""

    id: str
    about: str | None = Field(None, description="The user's dish it's about; None = kitchen")
    text: str
    multi: bool = Field(False, description="Several options may be picked")
    options: list[QuestionOption]
    why: str = Field(..., description="Why it's asked, e.g. 'Could change 3 of your suggestions'")


class QuestionsRequest(BaseModel):
    """The kitchen to ask about."""

    repertoire: list[UserDish] = Field(..., min_length=1, max_length=settings.max_kitchen_dishes)
    diet: Diet = Field(default_factory=Diet)
    have: Have = Field(default_factory=Have)
    dismissed: list[str] = Field(
        default_factory=list, max_length=100, description="Question ids already answered"
    )


class QuestionsResponse(BaseModel):
    """At most a few questions, most useful first. Often empty."""

    questions: list[Question]


class RelatedDish(BaseModel):
    """A catalog dish one step from the page's dish, with what changes (computed by code)."""

    id: str
    name: str
    cuisine: str
    summary: str
    new_techniques: list[str]
    new_ingredients: list[str]


class DishPageResponse(BaseModel):
    """A catalog dish, its full recipe when there is one, and dishes one step away."""

    dish: Dish
    recipe: Recipe | None = None
    related: list[RelatedDish] = Field(default_factory=list)


class DishIndexEntry(BaseModel):
    """One line of the public dish index (for the sitemap and the dish directory)."""

    id: str
    name: str
    cuisine: str
    region: str


class PasskeyOptions(BaseModel):
    """Options to hand to the browser's passkey prompt, and the id to finish with."""

    challenge_id: str
    options: dict[str, Any]


class PasskeyFinish(BaseModel):
    """The browser's passkey response (WebAuthn JSON), for a challenge we issued."""

    challenge_id: str = Field(..., min_length=8, max_length=64)
    credential: dict[str, Any]


class SessionResponse(BaseModel):
    """A bearer token for this device. Kept in the browser; sent as Authorization."""

    token: str


class Me(BaseModel):
    """Who's signed in (there's nothing else to know)."""

    signed_in: bool = True
    has_kitchen: bool
    kitchen_updated_at: str | None = None


class KitchenSync(BaseModel):
    """The web app's saved kitchen, as-is. Size-checked; re-validated when used."""

    kitchen: dict[str, Any]


class KitchenSyncResponse(BaseModel):
    """The synced kitchen and when it was saved."""

    kitchen: dict[str, Any] | None
    updated_at: str | None


EventName = Literal[
    "kitchen_built",
    "dish_opened",
    "cooked",
    "saved",
    "cook_mode",
    "shopping_shared",
    "installed",
    "pasted",
]


class FeedbackRequest(BaseModel):
    """A message from the in-app feedback box."""

    message: str = Field(..., min_length=3, max_length=settings.max_feedback_chars)
    page: str = Field(default="", max_length=200)


class UsageEventIn(BaseModel):
    """One thing the app did. Names are a fixed list, so no free text is ever stored."""

    name: EventName
    dish_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-z0-9_]+$")


class UsageEvents(BaseModel):
    """A small batch of events from one device."""

    device: str = Field(..., pattern=r"^[A-Za-z0-9-]{8,36}$")
    events: list[UsageEventIn] = Field(..., min_length=1, max_length=settings.max_events_per_batch)


class UsageStats(BaseModel):
    """Counts for the owner: who uses the app, who comes back, and what they do."""

    days: int
    devices: int
    returning_devices: int = Field(..., description="Devices active on 2+ different days")
    events: dict[str, int]
    top_dishes: list[tuple[str, int]] = Field(..., description="Most opened dishes")
    feedback: list[str] = Field(..., description="Newest feedback first")
