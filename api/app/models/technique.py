"""How-to cards for techniques: short, written once, reviewed like code."""

from pydantic import BaseModel, Field

from app.models.vocab import Technique


class TechniqueGuide(BaseModel):
    """A quick how-to for one technique."""

    id: Technique
    title: str = Field(..., max_length=60, description="'Blooming whole spices (tadka)'")
    steps: list[str] = Field(..., min_length=3, max_length=5, description="Each under ~20 words")
    tip: str = Field(..., max_length=160, description="The one thing people get wrong")
    watch_query: str = Field(..., max_length=80, description="A good video search query")
