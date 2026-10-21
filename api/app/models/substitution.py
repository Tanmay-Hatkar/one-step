"""Ingredient substitutions by role: acid for acid, fat for fat. Built once, used by code."""

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal[
    "acid",  # lemon, vinegar, tamarind, dried lime
    "heat",  # chilies, chili powder, hot sauce
    "aromatic",  # onion, garlic, ginger, shallot
    "warm_spice",  # cumin, cardamom, cinnamon, garam masala
    "herb",  # cilantro, parsley, basil, mint
    "umami",  # soy sauce, fish sauce, miso, stock
    "fat",  # ghee, butter, olive oil, coconut oil
    "dairy",  # yogurt, cream, milk, cheese
    "sweetener",  # sugar, honey, jaggery
    "thickener",  # cornstarch, flour, ground nuts
    "liquid",  # stock, coconut milk, wine
    "vegetable",
    "protein",  # never swapped: changing the protein is a different dish
    "starch",  # never swapped: changing the base is a different dish
    "garnish",
    "other",
]

# Roles where a swap would change what the dish *is*; the graph never offers these.
NEVER_SWAPPED: frozenset[str] = frozenset({"protein", "starch"})


class Substitute(BaseModel):
    """One stand-in and how to use it."""

    name: str = Field(..., min_length=2, max_length=40, description="Lowercase, singular")
    note: str = Field(default="", max_length=80, description="e.g. 'use half as much'")


class IngredientSwaps(BaseModel):
    """What an ingredient does in a dish, and what can stand in for it."""

    ingredient: str = Field(..., min_length=2, max_length=40)
    role: Role
    substitutes: list[Substitute] = Field(default_factory=list, max_length=4)
