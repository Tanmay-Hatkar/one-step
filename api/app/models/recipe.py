"""A full recipe for a catalog dish, from an openly licensed source, with attribution."""

from pydantic import BaseModel, Field


class Recipe(BaseModel):
    """The source recipe as written (lightly cleaned of wiki markup)."""

    title: str = Field(..., description="Title on the source")
    source_url: str
    revision: int = Field(..., description="Source revision id, so the exact text is traceable")
    ingredients: list[str] = Field(..., min_length=1, max_length=40)
    steps: list[str] = Field(..., min_length=1, max_length=30)
    source_name: str = "Wikibooks Cookbook"
    authors: str = "Wikibooks contributors"
    license: str = "CC BY-SA 4.0"
    license_url: str = "https://creativecommons.org/licenses/by-sa/4.0/"
