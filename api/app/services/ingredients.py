"""Ingredient normalization — so 'chicken leg' and 'chicken thigh' count as the same thing.

The graph asks "what would this person need that they don't already have?". That
only works if names line up, so both catalog and user ingredients pass through
`normalize` before comparison. Pure functions, no I/O.
"""

# Things every kitchen is assumed to have. Never counted as "new".
STAPLES: frozenset[str] = frozenset(
    {
        "salt",
        "water",
        "oil",
        "cooking oil",
        "vegetable oil",
        "neutral oil",
        "black pepper",
        "pepper",
        "sugar",
    }
)

# Exact-name aliases → canonical name.
ALIASES: dict[str, str] = {
    "chicken broth": "chicken stock",
    "broth": "chicken stock",
    "stock cube": "chicken stock",
    "broth cube": "chicken stock",
    "chicken stock cube": "chicken stock",
    "chicken broth cube": "chicken stock",
    "bouillon": "chicken stock",
    "chicken bouillon": "chicken stock",
    "bouillon cube": "chicken stock",
    "coriander leaf": "cilantro",
    "coriander leaves": "cilantro",
    "fresh coriander": "cilantro",
    "curd": "yogurt",
    "plain yogurt": "yogurt",
    "greek yogurt": "yogurt",
    "chilli powder": "chili powder",
    "red chili powder": "chili powder",
    "kashmiri chili powder": "chili powder",
    "scallion": "green onion",
    "spring onion": "green onion",
    "ghee": "ghee",
}

# If a name ends with one of these words, collapse it to that base.
# 'basmati rice' → 'rice', 'chicken thigh' → handled by PREFIX_BASES.
SUFFIX_BASES: tuple[str, ...] = ("rice", "onion", "tomato", "garlic", "ginger", "potato")

# If a name starts with one of these, collapse it to the base:
# 'chicken thigh', 'chicken drumstick' → 'chicken'; 'lemon juice' → 'lemon'.
PREFIX_BASES: dict[str, str] = {
    "chicken ": "chicken",
    "lemon ": "lemon",
    "lime ": "lime",
    "garlic ": "garlic",
    "ginger ": "ginger",
}
PREFIX_EXCEPTIONS: frozenset[str] = frozenset({"chicken stock"})

DROP_WORDS: tuple[str, ...] = ("fresh ", "dried ", "ground ", "whole ", "chopped ", "minced ")


def _singular(word: str) -> str:
    """Very small singularizer: 'tomatoes' → 'tomato', 'onions' → 'onion'."""
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def normalize(name: str) -> str:
    """Return the canonical comparison key for an ingredient name.

    Args:
        name: Any ingredient name, e.g. 'Chicken Drumsticks' or 'basmati rice'.

    Returns:
        A canonical lowercase name, e.g. 'chicken' or 'rice'.
    """
    text = " ".join(name.lower().strip().split())
    if text in ALIASES:
        return ALIASES[text]
    for word in DROP_WORDS:
        if text.startswith(word):
            text = text[len(word) :]
    words = text.split(" ")
    words[-1] = _singular(words[-1])
    text = " ".join(words)
    if text in ALIASES:
        return ALIASES[text]
    if text not in PREFIX_EXCEPTIONS:
        for prefix, base in PREFIX_BASES.items():
            if text.startswith(prefix):
                return base
    for base in SUFFIX_BASES:
        if text == base or text.endswith(" " + base):
            return base
    return text


def pantry_of(ingredient_lists: list[list[str]]) -> set[str]:
    """Return the normalized set of everything across several ingredient lists, plus staples.

    Args:
        ingredient_lists: e.g. the key_ingredients of each dish the user cooks.

    Returns:
        Normalized ingredient names the user is assumed to have.
    """
    pantry = {normalize(s) for s in STAPLES}
    for items in ingredient_lists:
        pantry.update(normalize(i) for i in items)
    return pantry


def missing_ingredients(needed: list[str], pantry: set[str]) -> list[str]:
    """Return the ingredients from `needed` that aren't in `pantry`, original names, deduped.

    Args:
        needed: A dish's key ingredients.
        pantry: Output of `pantry_of`.

    Returns:
        Missing ingredients in their original spelling, in order.
    """
    seen: set[str] = set()
    missing: list[str] = []
    for item in needed:
        key = normalize(item)
        if key in pantry or key in seen:
            continue
        seen.add(key)
        missing.append(item)
    return missing
