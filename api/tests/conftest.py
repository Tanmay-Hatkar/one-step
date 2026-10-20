"""Shared fixtures: small hand-built catalog, the founding user's dishes, a fake LLM."""

import os
import tempfile

# Isolate tests from the developer's .env and local database. Environment variables
# take precedence over .env in pydantic-settings, and must be set before app imports.
os.environ["OPENAI_API_KEY"] = ""
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from collections.abc import Callable
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db import init_db, make_session_factory
from app.llm.client import LLMError
from app.models.dish import Dish, UserDish
from app.repositories.llm_repository import LLMCacheRepository, LLMUsageRepository
from app.services.llm_gateway import LLMGateway

T = TypeVar("T", bound=BaseModel)


def make_dish(**overrides: Any) -> Dish:
    """Build a catalog dish with sensible defaults."""
    base: dict[str, Any] = {
        "id": "kabsa",
        "name": "Kabsa",
        "cuisine": "Saudi",
        "region": "Middle East",
        "family": "rice_with_protein",
        "protein": "chicken",
        "starch": "rice",
        "techniques": ["sear", "simmer", "rice_in_stock"],
        "equipment": ["stovetop"],
        "flavor": ["warm_spices", "tomato_base", "onion_base"],
        "key_ingredients": [
            "chicken leg",
            "basmati rice",
            "chicken stock",
            "onion",
            "tomato",
            "kabsa spice",
            "dried lime",
            "raisin",
        ],
        "effort": "weeknight",
        "time_minutes": 90,
        "allergens": [],
        "vegetarian": False,
        "summary": "Saudi spiced chicken and rice cooked in stock.",
    }
    base.update(overrides)
    return Dish.model_validate(base)


@pytest.fixture
def catalog() -> list[Dish]:
    """Six dishes: two close cousins, one far one, one needing an oven, one known, one twin."""
    return [
        make_dish(),
        make_dish(
            id="plov",
            name="Plov",
            cuisine="Uzbek",
            region="Central Asia",
            protein="lamb_or_goat",
            techniques=["sear", "braise", "rice_in_stock"],
            key_ingredients=["lamb shoulder", "rice", "carrot", "onion", "cumin", "chickpea"],
        ),
        make_dish(
            id="pad_thai",
            name="Pad Thai",
            cuisine="Thai",
            region="Southeast Asia",
            family="noodles",
            protein="shrimp",
            starch="rice_noodles",
            techniques=["boil", "stir_fry"],
            equipment=["stovetop", "wok"],
            flavor=["fish_sauce", "sweet", "citrus"],
            key_ingredients=[
                "rice noodle",
                "shrimp",
                "egg",
                "fish sauce",
                "tamarind paste",
                "peanut",
            ],
            allergens=["egg", "fish", "shellfish", "peanut"],
        ),
        make_dish(
            id="tandoori_chicken",
            name="Tandoori Chicken",
            cuisine="Indian",
            region="South Asia",
            family="roast_and_grill",
            starch="none",
            techniques=["marinate", "roast"],
            equipment=["oven"],
            flavor=["yogurt", "chili_heat", "warm_spices"],
            key_ingredients=["chicken leg", "yogurt", "lemon", "garam masala", "chili powder"],
            allergens=["dairy"],
        ),
        make_dish(
            id="chicken_biryani",
            name="Chicken Biryani",
            cuisine="Indian",
            region="South Asia",
            techniques=["marinate", "layered_dum"],
            effort="weekend",
            key_ingredients=[
                "chicken thigh",
                "basmati rice",
                "yogurt",
                "onion",
                "garam masala",
                "saffron",
            ],
            allergens=["dairy"],
        ),
        make_dish(
            id="chicken_pulao",
            name="Chicken Pulao",
            cuisine="Indian",
            region="South Asia",
            techniques=["marinate", "rice_in_stock"],
            flavor=["warm_spices", "onion_base"],
            key_ingredients=["chicken", "rice", "chicken stock", "onion", "garlic"],
        ),
    ]


@pytest.fixture
def chicken_and_rice() -> UserDish:
    """The founding user's weeknight dish."""
    return UserDish(
        name="Chicken leg with rice",
        notes="rice-cooker rice with garlic, onion, stock cube",
        family="rice_with_protein",
        protein="chicken",
        starch="rice",
        techniques=["marinate", "rice_in_stock"],
        equipment=["rice_cooker", "stovetop"],
        flavor=["warm_spices", "onion_base", "garlic_ginger"],
        key_ingredients=[
            "chicken leg",
            "rice",
            "garlic",
            "onion",
            "chicken stock",
            "turmeric",
            "cumin",
        ],
        effort="weeknight",
    )


@pytest.fixture
def settings() -> Settings:
    """Default settings, isolated from any local .env."""
    return Settings(_env_file=None, openai_api_key="test", daily_llm_call_cap=100)


@pytest.fixture
def session_factory() -> sessionmaker:
    """In-memory SQLite shared across connections."""
    from sqlalchemy import create_engine

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    init_db(engine)
    return make_session_factory(engine)


class FakeLLMClient:
    """Returns whatever `responder(schema, prompt)` builds; counts calls; can fail."""

    model = "fake-model"

    def __init__(self, responder: Callable[[type[BaseModel], str], BaseModel]) -> None:
        self.responder = responder
        self.calls = 0
        self.fail = False

    async def parse(self, *, instructions: str, prompt: str, schema: type[T]) -> T:
        self.calls += 1
        if self.fail:
            raise LLMError("boom")
        result = self.responder(schema, prompt)
        return schema.model_validate(result.model_dump())


@pytest.fixture
def make_gateway(session_factory: sessionmaker) -> Callable[..., LLMGateway]:
    """Factory: a real gateway (real cache + cap) around a fake client."""

    def _make(client: FakeLLMClient, cap: int = 100) -> LLMGateway:
        return LLMGateway(
            client, LLMCacheRepository(session_factory), LLMUsageRepository(session_factory), cap
        )

    return _make
