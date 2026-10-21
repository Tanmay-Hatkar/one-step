"""Human-readable phrases for vocabulary values — so prompts and UIs never show raw ids."""

TECHNIQUE_LABELS: dict[str, str] = {
    "marinate": "marinating",
    "spice_paste": "making a spice paste",
    "temper_spices": "blooming whole spices in hot oil",
    "sear": "searing",
    "pan_fry": "pan-frying",
    "stir_fry": "stir-frying",
    "deep_fry": "deep-frying",
    "roast": "roasting",
    "grill": "grilling",
    "braise": "braising",
    "simmer": "simmering",
    "steam": "steaming",
    "boil": "boiling",
    "bake": "baking",
    "rice_in_stock": "cooking the rice in stock",
    "plain_rice": "cooking plain rice",
    "layered_dum": "layering and slow-steaming under a seal",
    "scramble": "scrambling",
    "knead_dough": "kneading dough",
    "wrap_and_roll": "wrapping and rolling",
    "poach": "poaching",
    "blend_puree": "blending a sauce",
}


def technique_label(technique: str) -> str:
    """Return a readable phrase: 'rice_in_stock' → 'cooking the rice in stock'."""
    return TECHNIQUE_LABELS.get(technique, technique.replace("_", " "))


EQUIPMENT_LABELS: dict[str, str] = {
    "stovetop": "Stovetop",
    "oven": "Oven",
    "rice_cooker": "Rice cooker",
    "grill": "Grill or tandoor",
    "wok": "Wok",
    "pressure_cooker": "Pressure cooker",
    "blender": "Blender or mixer",
    "griddle": "Griddle or tawa",
    "steamer": "Steamer",
    "air_fryer": "Air fryer",
}


def equipment_label(item: str) -> str:
    """Return a readable name: 'pressure_cooker' → 'Pressure cooker'."""
    return EQUIPMENT_LABELS.get(item, item.replace("_", " ").capitalize())
