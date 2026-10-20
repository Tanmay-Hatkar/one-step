"""Allergens and vegetarian status, worked out from ingredients — a safety net in code.

The catalog's `allergens` and `vegetarian` fields were generated once by an LLM. A
hard filter can't trust that alone, so every dish is also checked against plain
keyword rules over its ingredients, and the two are combined conservatively:
an allergen is present if *either* says so; a dish is vegetarian only if *both* do.
Pure functions, no I/O.
"""

import re

from app.models.dish import Dish, UserDish
from app.models.vocab import Allergen

# Keywords that mean an ingredient contains the allergen (singular; plurals match too).
ALLERGEN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dairy": (
        "milk",
        "butter",
        "cream",
        "cheese",
        "paneer",
        "yogurt",
        "ghee",
        "curd",
        "kefir",
        "labneh",
        "feta",
        "parmesan",
        "mozzarella",
        "ricotta",
        "halloumi",
        "queso",
        "crema",
        "khoya",
        "malai",
    ),
    "egg": ("egg", "mayonnaise", "mayo"),
    "gluten": (
        "flour",
        "wheat",
        "bread",
        "breadcrumb",
        "panko",
        "pasta",
        "spaghetti",
        "noodle",
        "macaroni",
        "orzo",
        "couscous",
        "bulgur",
        "semolina",
        "barley",
        "farro",
        "freekeh",
        "soy sauce",
        "tortilla",
        "pita",
        "naan",
        "roti",
        "chapati",
        "paratha",
        "udon",
        "ramen",
        "seitan",
        "wonton",
        "dumpling wrapper",
        "phyllo",
        "pastry",
        "beer",
        "malt",
        "hoisin",
        "gochujang",
        "oyster sauce",
    ),
    "peanut": ("peanut", "groundnut"),
    "tree_nut": (
        "almond",
        "cashew",
        "walnut",
        "pecan",
        "pistachio",
        "hazelnut",
        "pine nut",
        "macadamia",
        "brazil nut",
    ),
    "soy": (
        "soy",
        "tofu",
        "edamame",
        "miso",
        "tempeh",
        "doenjang",
        "gochujang",
        "hoisin",
        "tamari",
    ),
    "fish": (
        "fish",
        "anchovy",
        "salmon",
        "tuna",
        "cod",
        "tilapia",
        "mackerel",
        "sardine",
        "bonito",
        "dashi",
        "katsuobushi",
        "worcestershire",
    ),
    "shellfish": (
        "shrimp",
        "prawn",
        "crab",
        "lobster",
        "crawfish",
        "crayfish",
        "clam",
        "mussel",
        "oyster",
        "scallop",
    ),
    "sesame": ("sesame", "tahini"),
}

# Ingredients that contain a keyword but not the allergen ('coconut milk' isn't dairy).
ALLERGEN_EXCEPTIONS: dict[str, tuple[str, ...]] = {
    "dairy": (
        "coconut",
        "almond milk",
        "oat milk",
        "soy milk",
        "peanut butter",
        "cocoa butter",
        "bean curd",
    ),
    "gluten": (
        "rice ",
        "corn",
        "chickpea",
        "gram flour",
        "tapioca",
        "glass noodle",
        "mung bean",
        "gluten-free",
        "gluten free",
    ),
    "fish": ("shellfish",),
}

# Any of these in an ingredient means the dish isn't vegetarian.
MEAT_KEYWORDS: tuple[str, ...] = (
    "chicken",
    "beef",
    "lamb",
    "goat",
    "mutton",
    "pork",
    "bacon",
    "ham",
    "sausage",
    "chorizo",
    "andouille",
    "pancetta",
    "prosciutto",
    "salami",
    "turkey",
    "duck",
    "veal",
    "lard",
    "gelatin",
    "squid",
    "octopus",
    *ALLERGEN_KEYWORDS["fish"],
    *ALLERGEN_KEYWORDS["shellfish"],
)

# Proteins that are compatible with a vegetarian diet.
VEGETARIAN_PROTEINS: frozenset[str] = frozenset(
    {"egg", "paneer_or_cheese", "tofu", "legumes", "none"}
)


def _has_word(text: str, keyword: str) -> bool:
    """True if `keyword` appears in `text` as a whole word (plural 's'/'es' allowed)."""
    return re.search(rf"\b{re.escape(keyword)}(e?s)?\b", text) is not None


def ingredient_allergens(ingredient: str) -> set[Allergen]:
    """Return the allergens one ingredient name implies.

    Args:
        ingredient: An ingredient name, e.g. 'fish sauce'.

    Returns:
        Allergens found, e.g. {'fish'}.
    """
    name = ingredient.lower().strip()
    found: set[Allergen] = set()
    for allergen, keywords in ALLERGEN_KEYWORDS.items():
        if any(exc in name for exc in ALLERGEN_EXCEPTIONS.get(allergen, ())):
            continue
        if any(_has_word(name, kw) for kw in keywords):
            found.add(allergen)  # type: ignore[arg-type]
    return found


def is_meat_ingredient(ingredient: str) -> bool:
    """True if an ingredient is meat, fish or seafood (or made from it, like stock)."""
    name = ingredient.lower().strip()
    if "shellfish" in name:
        return True
    return any(_has_word(name, kw) for kw in MEAT_KEYWORDS)


def text_mentions_allergen(text: str, allergens: set[str]) -> bool:
    """True if free text (e.g. an LLM-written diff) names any of the given allergens.

    Args:
        text: Text to scan.
        allergens: Allergen ids to look for.

    Returns:
        Whether any allergen keyword appears.
    """
    lowered = text.lower()
    for allergen in allergens:
        for keyword in ALLERGEN_KEYWORDS.get(allergen, ()):
            for match in re.finditer(rf"\b{re.escape(keyword)}(e?s)?\b", lowered):
                window = lowered[max(0, match.start() - 12) : match.end() + 12]
                if not any(exc in window for exc in ALLERGEN_EXCEPTIONS.get(allergen, ())):
                    return True
    return False


def with_safe_diet_facts(dish: Dish) -> Dish:
    """Return the dish with allergens and vegetarian status cross-checked against ingredients.

    Args:
        dish: A catalog dish as generated.

    Returns:
        A copy where allergens = tagged + inferred, and vegetarian is True only if the
        tag, the protein and every ingredient agree.
    """
    inferred: set[str] = set()
    for ingredient in dish.key_ingredients:
        inferred |= ingredient_allergens(ingredient)
    allergens = sorted(set(dish.allergens) | inferred)
    vegetarian = (
        dish.vegetarian
        and dish.protein in VEGETARIAN_PROTEINS
        and not any(is_meat_ingredient(i) for i in dish.key_ingredients)
    )
    return dish.model_copy(update={"allergens": allergens, "vegetarian": vegetarian})


def allows(dish: Dish, vegetarian: bool, avoid: set[str] | frozenset[str]) -> bool:
    """Hard diet rule: may this dish be shown?

    Args:
        dish: A catalog dish (already passed through `with_safe_diet_facts`).
        vegetarian: Whether the user eats vegetarian.
        avoid: Allergen ids the user avoids.

    Returns:
        False if the dish breaks any rule.
    """
    if vegetarian and not dish.vegetarian:
        return False
    return not (avoid & set(dish.allergens))


def user_dish_allows(dish: UserDish, vegetarian: bool, avoid: set[str] | frozenset[str]) -> bool:
    """Hard diet rule for one of the user's own dishes (judged from its parts alone).

    Args:
        dish: A dish the user cooks.
        vegetarian: Whether the user eats vegetarian.
        avoid: Allergen ids the user avoids.

    Returns:
        False if the dish breaks any rule.
    """
    if vegetarian and (
        dish.protein not in VEGETARIAN_PROTEINS
        or any(is_meat_ingredient(i) for i in dish.key_ingredients)
    ):
        return False
    found: set[str] = set()
    for ingredient in dish.key_ingredients:
        found |= ingredient_allergens(ingredient)
    return not (set(avoid) & found)
