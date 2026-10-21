"""Eval cases. Each one states what a correct answer must (and must not) contain.

Three suites:
- PARSE: free text → structured dishes (does the LLM capture *their* version?)
- DIFF: user dish + catalog dish → written changes (grounded, readable, no leaks?)
- END_TO_END: free text → cousins (does the whole pipeline suggest sensible dishes?)
"""

from typing import Any

FOUNDING_USER_TEXT = (
    "Most nights I make a whole chicken leg marinated in Indian spices, with regular rice "
    "made in an electric rice cooker with garlic, onion, a chicken broth cube and some basic "
    "spices. Some weekends I make a full chicken biryani."
)

PARSE_CASES: list[dict[str, Any]] = [
    {
        "id": "founding_user",
        "text": FOUNDING_USER_TEXT,
        "n_dishes": (2, 2),
        "dishes": [
            {
                "family": "rice_with_protein",
                "protein": "chicken",
                "starch": "rice",
                "techniques": ["marinate", "rice_in_stock"],
                "equipment": ["rice_cooker"],
                "ingredients": ["chicken stock", "garlic", "onion"],
                "not_said": ["turmeric", "garam masala", "oil", "water"],
                "has_guesses": True,
                "matched": None,
            },
            {
                "protein": "chicken",
                "starch": "rice",
                "matched": "chicken_biryani",
                "effort": "weekend",
            },
        ],
    },
    {
        "id": "flavoured_rice",
        "text": "Most nights I make a flavoured rice in the rice cooker. I fry chopped onion "
        "and a lot of garlic in a little oil or ghee until golden, then add the washed rice and "
        "stir it for a minute. Then it all goes into the rice cooker with water and a crumbled "
        "chicken broth cube, sometimes with a bay leaf or a few whole spices. The cooker does "
        "the rest. I usually eat it with my chicken leg marinated in Indian spices.",
        "n_dishes": (1, 1),
        "dishes": [
            {
                "protein": "chicken",
                "starch": "rice",
                "techniques": ["rice_in_stock", "marinate"],
                "equipment": ["rice_cooker"],
                "ingredients": ["chicken stock", "garlic", "onion", "bay leaf"],
                "not_said": ["cumin", "cardamom", "clove", "cinnamon", "oil", "water"],
                "has_guesses": True,
            }
        ],
    },
    {
        "id": "dal_chawal",
        "text": "I usually make dal tadka with plain rice. Toor dal in a pressure cooker, "
        "then a tadka of cumin, garlic and dried red chilies in ghee.",
        "n_dishes": (1, 2),
        "dishes": [
            {
                "family": "lentils_and_beans",
                "protein": "legumes",
                "techniques": ["temper_spices"],
                "equipment": ["pressure_cooker"],
            }
        ],
    },
    {
        "id": "pasta_student",
        "text": "Honestly just pasta. Spaghetti with garlic, olive oil and chili flakes, "
        "sometimes with a jar of tomato sauce.",
        "n_dishes": (1, 2),
        "dishes": [
            {"family": "noodles", "starch": "pasta", "protein": "none", "ingredients": ["garlic"]}
        ],
    },
    {
        "id": "eggs_breakfast",
        "text": "Egg bhurji with onions, tomatoes and green chili, eaten with toast.",
        "n_dishes": (1, 1),
        "dishes": [{"family": "egg_dishes", "protein": "egg", "techniques": ["scramble"]}],
    },
    {
        "id": "stir_fry",
        "text": "Chicken stir fry in a wok with soy sauce, ginger, garlic and whatever "
        "veggies I have, served over jasmine rice.",
        "n_dishes": (1, 1),
        "dishes": [
            {
                "protein": "chicken",
                "techniques": ["stir_fry"],
                "equipment": ["wok"],
                "ingredients": ["soy sauce", "ginger"],
            }
        ],
    },
    {
        "id": "oven_roast",
        "text": "Sunday roast chicken in the oven with lemon, garlic and rosemary, "
        "with roast potatoes.",
        "n_dishes": (1, 1),
        "dishes": [
            {
                "family": "roast_and_grill",
                "protein": "chicken",
                "techniques": ["roast"],
                "equipment": ["oven"],
                "effort": "weekend",
            }
        ],
    },
    {
        "id": "two_dishes_casual",
        "text": "rajma chawal on weekdays and paneer butter masala when friends come over",
        "n_dishes": (2, 2),
        "dishes": [{"protein": "legumes"}, {"protein": "paneer_or_cheese"}],
    },
    {
        "id": "known_dish_by_name",
        "text": "I make a mean shakshuka.",
        "n_dishes": (1, 1),
        "dishes": [{"family": "egg_dishes", "matched": "shakshuka"}],
    },
]

DIFF_CASES: list[dict[str, Any]] = [
    {"id": "rice_to_kabsa", "anchor": "founding_rice", "dish": "kabsa"},
    {"id": "rice_to_arroz", "anchor": "founding_rice", "dish": "arroz_con_pollo"},
    {"id": "rice_to_hainanese", "anchor": "founding_rice", "dish": "hainanese_chicken_rice"},
    {"id": "rice_to_jollof", "anchor": "founding_rice", "dish": "jollof_rice_with_chicken"},
    {"id": "rice_to_plov", "anchor": "founding_rice", "dish": "plov"},
    {"id": "rice_to_tandoori", "anchor": "founding_rice", "dish": "tandoori_chicken"},
    {"id": "dal_to_chana", "anchor": "dal", "dish": "chana_masala"},
    {"id": "dal_to_khichdi", "anchor": "dal", "dish": "khichdi"},
]

ANCHORS: dict[str, dict[str, Any]] = {
    "founding_rice": {
        "name": "Chicken leg with rice",
        "notes": "chicken leg in Indian spices; rice-cooker rice with garlic, onion, stock cube",
        "family": "rice_with_protein",
        "protein": "chicken",
        "starch": "rice",
        "techniques": ["marinate", "rice_in_stock"],
        "equipment": ["rice_cooker", "stovetop"],
        "flavor": ["warm_spices", "onion_base", "garlic_ginger", "chili_heat"],
        "key_ingredients": [
            "chicken leg",
            "rice",
            "garlic",
            "onion",
            "chicken stock",
            "turmeric",
            "chili powder",
            "cumin",
            "coriander",
            "garam masala",
        ],
        "effort": "weeknight",
    },
    "dal": {
        "name": "Dal tadka",
        "notes": "toor dal in a pressure cooker, tadka of cumin, garlic, red chili in ghee",
        "family": "lentils_and_beans",
        "protein": "legumes",
        "starch": "rice",
        "techniques": ["boil", "temper_spices"],
        "equipment": ["pressure_cooker", "stovetop"],
        "flavor": ["cumin_coriander", "garlic_ginger", "chili_heat"],
        "key_ingredients": [
            "toor dal",
            "rice",
            "cumin",
            "garlic",
            "dried red chili",
            "ghee",
            "turmeric",
        ],
        "effort": "weeknight",
    },
}


def parse_text(case_id: str) -> str:
    """The text of a parse case, by id (so reordering cases can't break other suites)."""
    return next(c["text"] for c in PARSE_CASES if c["id"] == case_id)


END_TO_END_CASES: list[dict[str, Any]] = [
    {
        "id": "founding_user",
        "text": FOUNDING_USER_TEXT,
        "expect_family": "rice_with_protein",
        "min_family_hits": 3,
        "min_regions": 3,
    },
    {
        "id": "dal_cook",
        "text": parse_text("dal_chawal"),
        "expect_family": "lentils_and_beans",
        "min_family_hits": 2,
        "min_regions": 2,
    },
    {
        "id": "noodle_cook",
        "text": "Hakka noodles with chicken, soy sauce and chili sauce tossed in a wok.",
        "expect_family": "noodles",
        "min_family_hits": 2,
        "min_regions": 2,
    },
    {
        "id": "egg_cook",
        "text": parse_text("eggs_breakfast"),
        "expect_family": "egg_dishes",
        "min_family_hits": 2,
        "min_regions": 2,
    },
]
