"""Controlled vocabularies for the dish graph.

Dishes are compared by these closed sets, not by free text. That's what makes
"one step away" a deterministic computation instead of an LLM guess: the LLM maps
messy language onto these values once, and code does the reasoning after that.
"""

from typing import Literal

DishFamily = Literal[
    "rice_with_protein",  # biryani, kabsa, plov, jollof, arroz con pollo, paella
    "curry_and_stew",  # butter chicken, tagine, adobo, goulash
    "noodles",  # pad thai, lo mein, ramen, pasta dishes
    "flatbread_and_wraps",  # shawarma wrap, kathi roll, quesadilla, tacos
    "egg_dishes",  # shakshuka, egg bhurji, frittata, tamagoyaki
    "roast_and_grill",  # tandoori chicken, peri-peri, yakitori, roast chicken
    "lentils_and_beans",  # dal, chana masala, feijoada, chili
    "soups",  # pho, chicken soup, tom yum, harira
]

Technique = Literal[
    "marinate",
    "spice_paste",  # grind or blend a wet masala / curry paste
    "temper_spices",  # bloom whole spices in hot fat (tadka)
    "sear",
    "pan_fry",
    "stir_fry",
    "deep_fry",
    "roast",
    "grill",
    "braise",
    "simmer",
    "steam",
    "boil",
    "bake",
    "rice_in_stock",  # rice cooked by absorbing seasoned stock
    "plain_rice",
    "layered_dum",  # layered and slow-steamed under a seal
    "scramble",
    "knead_dough",
    "wrap_and_roll",
    "poach",
    "blend_puree",
]

Equipment = Literal[
    "stovetop",
    "oven",
    "rice_cooker",
    "grill",
    "wok",
    "pressure_cooker",
    "blender",
    "griddle",
    "steamer",
    "air_fryer",
]

Protein = Literal[
    "chicken",
    "lamb_or_goat",
    "beef",
    "pork",
    "fish",
    "shrimp",
    "egg",
    "paneer_or_cheese",
    "tofu",
    "legumes",
    "none",
]

Starch = Literal[
    "rice",
    "wheat_noodles",
    "rice_noodles",
    "pasta",
    "flatbread",
    "bread",
    "potato",
    "none",
]

Flavor = Literal[
    "warm_spices",  # garam masala, cinnamon, cardamom, clove
    "cumin_coriander",
    "chili_heat",
    "garlic_ginger",
    "onion_base",
    "tomato_base",
    "yogurt",
    "soy_umami",
    "fish_sauce",
    "citrus",
    "coconut",
    "fresh_herbs",
    "smoky",
    "saffron",
    "sesame",
    "butter_cream",
    "vinegar_sour",
    "fermented_chili",  # gochujang, doubanjiang, sambal
    "sweet",
]

Allergen = Literal[
    "dairy",
    "egg",
    "gluten",
    "peanut",
    "tree_nut",
    "soy",
    "fish",
    "shellfish",
    "sesame",
]

Effort = Literal["weeknight", "weekend"]

Region = Literal[
    "South Asia",
    "Middle East",
    "Central Asia",
    "East Asia",
    "Southeast Asia",
    "Africa",
    "Europe",
    "Latin America",
    "North America",
    "Caribbean",
]
