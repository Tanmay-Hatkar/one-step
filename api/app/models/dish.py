"""Dish shapes: catalog dishes, the user's own dishes, and the computed difference."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.vocab import (
    Allergen,
    DishFamily,
    Effort,
    Equipment,
    Flavor,
    Protein,
    Region,
    Starch,
    Technique,
)


class DishParts(BaseModel):
    """The structural parts every dish is broken into. Shared by catalog and user dishes."""

    family: DishFamily
    protein: Protein
    starch: Starch
    techniques: list[Technique] = Field(..., min_length=1, max_length=8)
    equipment: list[Equipment] = Field(..., min_length=1, max_length=4)
    flavor: list[Flavor] = Field(..., min_length=1, max_length=8)
    key_ingredients: list[str] = Field(
        ...,
        min_length=2,
        max_length=16,
        description="Simple lowercase singular names, e.g. 'chicken thigh', 'chicken stock'.",
    )
    effort: Effort


class Dish(DishParts):
    """A dish in the catalog (the seed graph)."""

    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Stable slug, e.g. 'kabsa'")
    name: str = Field(..., min_length=2, max_length=60)
    cuisine: str = Field(..., min_length=2, max_length=40, description="e.g. 'Saudi'")
    region: Region
    time_minutes: int = Field(..., ge=5, le=480)
    allergens: list[Allergen] = Field(default_factory=list)
    vegetarian: bool
    summary: str = Field(..., min_length=10, max_length=200)


class UserDish(DishParts):
    """A dish the user already cooks — *their* version, parsed from their own words."""

    name: str = Field(..., min_length=2, max_length=80, description="What the user calls it")
    notes: str = Field(
        default="",
        max_length=300,
        description="How they make it: 'rice-cooker rice with garlic, onion, stock cube'.",
    )
    matched_dish_id: str | None = Field(
        default=None, description="Catalog id when this is a known dish (e.g. 'chicken_biryani')."
    )
    source: Literal["described", "cooked"] = Field(
        default="described",
        description="'described' = in their own words; 'cooked' = a suggestion they marked cooked",
    )


class Delta(BaseModel):
    """What changes between one of the user's dishes and a catalog dish. Computed by code."""

    anchor_name: str = Field(..., description="The user's dish this cousin is closest to")
    shared_techniques: list[Technique]
    new_techniques: list[Technique]
    dropped_techniques: list[Technique]
    new_equipment: list[Equipment]
    new_ingredients: list[str]
    new_flavors: list[Flavor]
    same_protein: bool
    same_starch: bool
    same_family: bool
    score: float = Field(..., description="Higher = closer to what the user already cooks")
    is_one_step: bool
