"""Paste a recipe: link detection, page reading, validation in code, and the route."""

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.deps import get_recipe_import_service
from app.llm.client import LLMError
from app.main import create_app
from app.models.api import Diet
from app.repositories.page_repository import LinkNotSupported, PageRepository, PageUnreadable
from app.services.cousin_service import CousinService
from app.services.graph_service import GraphService
from app.services.llm_gateway import DailyCapExceeded
from app.services.recipe_import_service import (
    NotARecipe,
    PhotoRejected,
    RecipeImportService,
    _ReadRecipe,
    breaks_diet,
    link_in,
    photo_type,
    to_dish,
)
from app.services.recipe_page import recipe_text_from_html
from tests.conftest import FakeLLMClient

KABSA_TEXT = "Chicken kabsa. 4 chicken legs, 2 cups basmati rice, 2 tbsp butter… Sear, simmer."


def read_recipe(**overrides: Any) -> _ReadRecipe:
    """What the model would return for a kabsa recipe."""
    base: dict[str, Any] = {
        "is_recipe": True,
        "name": "Chicken Kabsa",
        "cuisine": "Saudi",
        "region": "Middle East",
        "summary": "Spiced chicken and rice cooked together in stock.",
        "time_minutes": 75,
        "family": "rice_with_protein",
        "protein": "chicken",
        "starch": "rice",
        "techniques": ["sear", "simmer", "rice_in_stock"],
        "equipment": ["stovetop"],
        "flavor": ["warm_spices", "tomato_base"],
        "key_ingredients": ["chicken leg", "basmati rice", "onion", "Salt", "dried lime", "onion"],
        "effort": "weeknight",
        "ingredients": ["4 chicken legs", "2 cups basmati rice", "2 tbsp butter", "  "],
        "steps": ["Sear the chicken.", "Add rice and stock; simmer 20 minutes."],
    }
    base.update(overrides)
    return _ReadRecipe.model_validate(base)


class FakePages:
    """Stands in for the page reader: returns fixed HTML or raises."""

    def __init__(self, html: str = "", error: Exception | None = None) -> None:
        self.html, self.error, self.urls = html, error, []

    async def read(self, url: str) -> str:
        self.urls.append(url)
        if self.error:
            raise self.error
        return self.html


def make_service(catalog, settings, make_gateway, read: _ReadRecipe, pages=None):
    """The real service around a fake model that reads `read` and writes a fixed diff."""

    def responder(schema: type[BaseModel], prompt: str) -> BaseModel:
        if schema is _ReadRecipe:
            return read
        return schema(changes=["Add a dried lime."], keep_line="Your rice stays the same.")

    client = FakeLLMClient(responder)
    gateway = make_gateway(client)
    graph = GraphService(catalog, settings)
    service = RecipeImportService(
        gateway, graph, CousinService(graph, gateway), pages or FakePages(), 8000, 200
    )
    return service, client


# --- link or text? -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/kabsa", "https://example.com/kabsa"),
        ("Best kabsa ever https://example.com/kabsa.", "https://example.com/kabsa"),
        ("Chicken kabsa: sear the chicken, add rice", None),
        ("https://a.example/1 and https://b.example/2", None),
        ("https://example.com/kabsa " + "then a long recipe follows " * 20, None),
    ],
)
def test_link_in(text: str, expected: str | None) -> None:
    assert link_in(text, 200) == expected


# --- reading a page ------------------------------------------------------------------

JSON_LD_PAGE = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"WebPage","name":"Blog"},
 {"@type":["Recipe"],"name":"Chicken &amp; Rice","totalTime":"PT45M",
  "recipeIngredient":["2 cups rice","1 <b>onion</b>"],
  "recipeInstructions":[{"@type":"HowToSection","itemListElement":[
     {"@type":"HowToStep","text":"Fry the onion."}]},"Add rice."]}]}
</script></head><body><p>Ten paragraphs about my holiday.</p></body></html>"""


def test_page_with_json_ld_gives_the_structured_recipe() -> None:
    text = recipe_text_from_html(JSON_LD_PAGE, 8000)
    assert "Recipe: Chicken & Rice" in text
    assert "- 1 onion" in text
    assert "1. Fry the onion." in text and "2. Add rice." in text
    assert "holiday" not in text


def test_page_without_json_ld_starts_near_the_ingredients() -> None:
    html = (
        "<html><script>var x = 'ignore me';</script><body>"
        + "<p>My life story.</p>" * 200
        + "<h2>Ingredients</h2><li>2 cups rice</li></body></html>"
    )
    text = recipe_text_from_html(html, 8000)
    assert "ignore me" not in text
    assert "2 cups rice" in text
    assert len(text) < 600


def test_page_text_is_capped() -> None:
    assert len(recipe_text_from_html("<p>" + "rice " * 5000 + "</p>", 100)) == 100


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://[::1]/",
        "http://example.com:8080/",
        "http://user:pass@example.com/",
        "not a link",
    ],
)
def test_private_and_odd_links_are_refused_without_fetching(url: str) -> None:
    pages = PageRepository(2.0, 1000, 1, "test", ["instagram.com"])
    with pytest.raises(PageUnreadable):
        asyncio.run(pages.read(url))


def test_login_walled_sites_get_their_own_error() -> None:
    pages = PageRepository(2.0, 1000, 1, "test", ["instagram.com"])
    with pytest.raises(LinkNotSupported):
        asyncio.run(pages.read("https://www.instagram.com/reel/abc/"))


# --- validation in code --------------------------------------------------------------


def test_to_dish_cleans_and_works_out_diet_facts_in_code() -> None:
    dish, recipe = to_dish(read_recipe())
    assert dish.id.startswith("pasted_")
    assert dish.key_ingredients == ["chicken leg", "basmati rice", "onion", "dried lime"]
    # Butter is only in the full ingredient lines, and the model has no say in allergens.
    assert dish.allergens == ["dairy"]
    assert dish.vegetarian is False
    assert recipe.ingredients == ["4 chicken legs", "2 cups basmati rice", "2 tbsp butter"]


def test_vegetarian_needs_every_ingredient_to_agree() -> None:
    veg = read_recipe(protein="legumes", key_ingredients=["chickpea", "rice", "onion"])
    assert to_dish(veg)[0].vegetarian is False  # the lines still say chicken legs
    veg = veg.model_copy(update={"ingredients": ["1 can chickpeas", "2 cups rice"]})
    assert to_dish(veg)[0].vegetarian is True


def test_same_recipe_gets_the_same_id() -> None:
    assert to_dish(read_recipe())[0].id == to_dish(read_recipe(summary="Other words here."))[0].id


@pytest.mark.parametrize(
    "overrides",
    [{"is_recipe": False}, {"key_ingredients": ["salt"]}, {"techniques": []}, {"name": ""}],
)
def test_thin_or_missing_recipes_are_rejected(overrides: dict) -> None:
    with pytest.raises(NotARecipe):
        to_dish(read_recipe(**overrides))


def test_breaks_diet_lists_each_broken_rule() -> None:
    dish, _ = to_dish(read_recipe())
    assert breaks_diet(dish, Diet()) == []
    assert breaks_diet(dish, Diet(vegetarian=True, avoid=["dairy", "soy"])) == [
        "dairy",
        "vegetarian",
    ]


# --- the service ---------------------------------------------------------------------


async def test_pasted_text_becomes_a_diff_from_your_kitchen(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, client = make_service(catalog, settings, make_gateway, read_recipe())
    result = await service.paste(KABSA_TEXT, [chicken_and_rice])
    assert result.cousin.diff.headline == "Chicken Kabsa: your chicken leg with rice, but…"
    assert result.cousin.delta.anchor_name == "Chicken leg with rice"
    assert result.cousin.delta.is_one_step
    assert "dried lime" in result.cousin.delta.new_ingredients
    assert result.recipe.source_url is None
    assert result.breaks_diet == []
    assert client.calls == 2  # one to read the recipe, one to write the diff


async def test_a_link_is_fetched_and_remembered_as_the_source(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    pages = FakePages(JSON_LD_PAGE)
    service, _ = make_service(catalog, settings, make_gateway, read_recipe(), pages)
    result = await service.paste("Look https://example.com/kabsa", [chicken_and_rice])
    assert pages.urls == ["https://example.com/kabsa"]
    assert result.recipe.source_url == "https://example.com/kabsa"


async def test_a_dish_that_breaks_the_diet_is_flagged_not_hidden(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, _ = make_service(catalog, settings, make_gateway, read_recipe())
    result = await service.paste(KABSA_TEXT, [chicken_and_rice], Diet(avoid=["dairy"]))
    assert result.breaks_diet == ["dairy"]
    assert result.cousin.diff.changes == ["Add a dried lime."]


async def test_diff_falls_back_when_the_model_fails_after_reading(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, client = make_service(catalog, settings, make_gateway, read_recipe())

    original = client.responder

    def flaky(schema: type[BaseModel], prompt: str) -> BaseModel:
        if schema is not _ReadRecipe:
            raise LLMError("boom")
        return original(schema, prompt)

    client.responder = flaky
    result = await service.paste(KABSA_TEXT, [chicken_and_rice])
    assert result.cousin.diff.keep_line == "Everything else is how you already do it."


async def test_an_empty_page_is_not_a_recipe(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, client = make_service(
        catalog, settings, make_gateway, read_recipe(), FakePages("<html></html>")
    )
    with pytest.raises(NotARecipe):
        await service.paste("https://example.com/nothing", [chicken_and_rice])
    assert client.calls == 0


# --- a photo or screenshot --------------------------------------------------------------

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64


def test_photo_type_goes_by_the_bytes_not_the_label() -> None:
    assert photo_type(JPEG) == "image/jpeg"
    assert photo_type(PNG) == "image/png"
    assert photo_type(WEBP) == "image/webp"
    assert photo_type(b"<svg onload=alert(1)>") is None
    assert photo_type(b"") is None


async def test_a_photo_is_sent_to_the_model_and_written_up(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, client = make_service(catalog, settings, make_gateway, read_recipe())
    result = await service.paste_photo(JPEG, [chicken_and_rice])
    assert result.cousin.dish.name == "Chicken Kabsa"
    assert result.recipe.source_url is None
    assert client.images[0].media_type == "image/jpeg" and client.images[0].data == JPEG
    assert client.images[1] is None  # the diff is written from parts, not the picture


async def test_two_different_photos_are_not_served_from_one_cache_entry(
    catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, client = make_service(catalog, settings, make_gateway, read_recipe())
    await service.paste_photo(JPEG, [chicken_and_rice])
    await service.paste_photo(JPEG, [chicken_and_rice])
    assert client.calls == 2  # second time: both answers cached
    await service.paste_photo(PNG, [chicken_and_rice])
    assert client.calls == 3  # a new picture is read again; the diff is still cached


@pytest.mark.parametrize("photo", [b"not a picture", b"\xff\xd8\xff" + b"\x00" * 5_000_000])
async def test_bad_or_huge_photos_are_rejected_before_any_model_call(
    catalog, settings, make_gateway, chicken_and_rice, photo
) -> None:
    service, client = make_service(catalog, settings, make_gateway, read_recipe())
    with pytest.raises(PhotoRejected):
        await service.paste_photo(photo, [chicken_and_rice])
    assert client.calls == 0


# --- the route -----------------------------------------------------------------------


class StubImport:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def paste(self, *args: Any, **kwargs: Any):
        raise self.error

    async def paste_photo(self, *args: Any, **kwargs: Any):
        raise self.error


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        test_client.app_ref = app  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()


def test_route_returns_the_pasted_dish(
    client, catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, _ = make_service(catalog, settings, make_gateway, read_recipe())
    client.app_ref.dependency_overrides[get_recipe_import_service] = lambda: service
    response = client.post(
        "/api/paste", json={"text": KABSA_TEXT, "repertoire": [chicken_and_rice.model_dump()]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cousin"]["dish"]["name"] == "Chicken Kabsa"
    assert body["recipe"]["steps"][0] == "Sear the chicken."


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotARecipe(), 422),
        (PageUnreadable(), 422),
        (LinkNotSupported(), 422),
        (DailyCapExceeded(), 503),
        (LLMError(), 502),
    ],
)
def test_route_errors_map_to_status(client, chicken_and_rice, error, status) -> None:
    client.app_ref.dependency_overrides[get_recipe_import_service] = lambda: StubImport(error)
    response = client.post(
        "/api/paste", json={"text": KABSA_TEXT, "repertoire": [chicken_and_rice.model_dump()]}
    )
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)


def test_route_needs_a_kitchen(client) -> None:
    assert client.post("/api/paste", json={"text": KABSA_TEXT, "repertoire": []}).status_code == 422


def test_photo_route_returns_the_dish(
    client, catalog, settings, make_gateway, chicken_and_rice
) -> None:
    service, _ = make_service(catalog, settings, make_gateway, read_recipe())
    client.app_ref.dependency_overrides[get_recipe_import_service] = lambda: service
    kitchen = json.dumps({"repertoire": [chicken_and_rice.model_dump()]})
    response = client.post(
        "/api/paste/photo",
        files={"photo": ("shot.jpg", JPEG, "image/jpeg")},
        data={"kitchen": kitchen},
    )
    assert response.status_code == 200
    assert response.json()["cousin"]["dish"]["name"] == "Chicken Kabsa"


@pytest.mark.parametrize(
    ("error", "status"),
    [(PhotoRejected(), 422), (NotARecipe(), 422), (DailyCapExceeded(), 503), (LLMError(), 502)],
)
def test_photo_route_errors_map_to_status(client, chicken_and_rice, error, status) -> None:
    client.app_ref.dependency_overrides[get_recipe_import_service] = lambda: StubImport(error)
    kitchen = json.dumps({"repertoire": [chicken_and_rice.model_dump()]})
    response = client.post(
        "/api/paste/photo",
        files={"photo": ("s.jpg", JPEG, "image/jpeg")},
        data={"kitchen": kitchen},
    )
    assert response.status_code == status


def test_photo_route_needs_a_valid_kitchen(client) -> None:
    response = client.post(
        "/api/paste/photo",
        files={"photo": ("s.jpg", JPEG, "image/jpeg")},
        data={"kitchen": "{not json"},
    )
    assert response.status_code == 422
