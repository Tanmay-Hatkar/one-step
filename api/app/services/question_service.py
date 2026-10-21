"""Follow-up questions: code picks the few whose answers would change the suggestions most.

Every candidate question comes from a fixed bank, and each answer is a small patch to
the kitchen. To score a question we apply each answer, re-run the graph, and measure
how much the suggestions move. A question nobody's answer would change is never asked.
No LLM call: the wording is fixed text, so it's free, instant and testable.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.config import Settings
from app.models.api import Diet, Have, Patch, Question, QuestionOption
from app.models.dish import UserDish
from app.models.labels import equipment_label
from app.services.cousin_service import to_owned, to_rule
from app.services.graph_service import DietRule, GraphService, Owned

logger = logging.getLogger(__name__)

# Equipment worth asking about, in the order a home cook is most likely to have it.
ASKABLE_EQUIPMENT = (
    "oven",
    "pressure_cooker",
    "blender",
    "wok",
    "rice_cooker",
    "air_fryer",
    "griddle",
    "grill",
    "steamer",
)
MAX_EQUIPMENT_OPTIONS = 5
MAX_TECHNIQUES = 8  # DishParts.techniques max_length

MEATY = {"chicken", "lamb_or_goat", "beef", "pork", "fish", "shrimp", "paneer_or_cheese", "tofu"}
PROTEIN_WORDS = {
    "chicken": "chicken",
    "lamb_or_goat": "meat",
    "beef": "beef",
    "pork": "pork",
    "fish": "fish",
    "shrimp": "shrimp",
    "paneer_or_cheese": "paneer",
    "tofu": "tofu",
}


@dataclass(frozen=True)
class TechniqueQuestion:
    """'Do you …?' — a Yes adds the technique to that dish."""

    technique: str
    text: str  # may use {protein}
    applies: Callable[[UserDish], bool]


TECHNIQUE_QUESTIONS: tuple[TechniqueQuestion, ...] = (
    TechniqueQuestion(
        "marinate",
        "Do you marinate the {protein} before cooking it?",
        lambda d: d.protein in MEATY,
    ),
    TechniqueQuestion(
        "sear",
        "Do you brown the {protein} before it goes in?",
        lambda d: (
            d.protein in MEATY and d.family in {"curry_and_stew", "rice_with_protein", "soups"}
        ),
    ),
    TechniqueQuestion(
        "temper_spices",
        "Do you sizzle whole spices or seeds (like cumin or mustard seeds) in hot oil?",
        lambda d: d.family in {"lentils_and_beans", "curry_and_stew", "rice_with_protein"},
    ),
    TechniqueQuestion(
        "spice_paste",
        "Do you grind or blend a paste, like ginger-garlic or a curry paste?",
        lambda d: d.family in {"curry_and_stew", "rice_with_protein", "roast_and_grill"},
    ),
    TechniqueQuestion(
        "knead_dough",
        "Do you make the flatbread yourself?",
        lambda d: d.starch == "flatbread",
    ),
)

# (label, protein, allergen that rules it out, needs non-vegetarian)
PROTEIN_CHOICES = (
    ("Chicken", "chicken", None, True),
    ("Egg", "egg", "egg", False),
    ("Paneer", "paneer_or_cheese", "dairy", False),
    ("Tofu", "tofu", "soy", False),
    ("Chickpeas or beans", "legumes", None, False),
)
PROTEIN_FAMILIES = {"rice_with_protein", "noodles", "curry_and_stew", "soups"}


@dataclass(frozen=True)
class _Signature:
    """What the user would see: top suggestions and the one-step set."""

    top: frozenset[str]
    one_step: frozenset[str]


def apply_patch(
    repertoire: list[UserDish], have: Have, patch: Patch
) -> tuple[list[UserDish], Have]:
    """Apply one answer. The web app does the same thing in `applyPatch`.

    Args:
        repertoire: The user's dishes.
        have: What else they have.
        patch: The answer's effect.

    Returns:
        New (repertoire, have); the inputs are not modified.
    """
    dishes = list(repertoire)
    if patch.dish is not None and patch.dish < len(dishes):
        dish = dishes[patch.dish]
        techniques = list(dict.fromkeys([*dish.techniques, *patch.add_techniques]))
        update: dict[str, object] = {"techniques": techniques[:MAX_TECHNIQUES]}
        if patch.protein is not None:
            update["protein"] = patch.protein
        dishes[patch.dish] = dish.model_copy(update=update)
    if patch.add_equipment:
        equipment = list(dict.fromkeys([*have.equipment, *patch.add_equipment]))
        have = have.model_copy(update={"equipment": equipment})
    return dishes, have


class QuestionService:
    """Chooses up to `max_questions` follow-ups by how much each could change."""

    def __init__(self, graph: GraphService, settings: Settings) -> None:
        """Args: graph service, settings (max_questions, question_min_gain, question_top_k)."""
        self._graph = graph
        self._settings = settings

    def ask(
        self,
        repertoire: list[UserDish],
        diet: Diet | None = None,
        have: Have | None = None,
        dismissed: set[str] | None = None,
    ) -> list[Question]:
        """Return the most useful questions, best first (often fewer than the max).

        Args:
            repertoire: The user's dishes.
            diet: Hard diet rule (also filters protein options).
            have: What else they have.
            dismissed: Question ids already answered; never asked again.

        Returns:
            Questions whose answers would move the suggestions at least `question_min_gain`.
        """
        diet = diet or Diet()
        have = have or Have()
        rule = to_rule(diet)
        base = self._signature(repertoire, rule, to_owned(have))

        scored: list[tuple[float, Question]] = []
        for question in self._candidates(repertoire, diet, have):
            if question.id in (dismissed or set()):
                continue
            result = self._score(question, repertoire, have, rule, base)
            if result is not None:
                scored.append(result)

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [q for _, q in scored[: self._settings.max_questions]]

    def _score(
        self,
        question: Question,
        repertoire: list[UserDish],
        have: Have,
        rule: DietRule,
        base: _Signature,
    ) -> tuple[float, Question] | None:
        """(gain, question as shown) — or None if it isn't worth asking."""
        effects: list[tuple[float, int, QuestionOption]] = []
        for option in question.options:
            if option.patch == Patch():
                continue  # "No" / "None of these" changes nothing by definition
            dishes, owned = apply_patch(repertoire, have, option.patch)
            after = self._signature(dishes, rule, to_owned(owned))
            effects.append((self._change(base, after), len(base.top - after.top), option))

        if question.multi:
            # Keep only options that matter on their own, most useful first.
            useful = sorted((e for e in effects if e[0] > 0), key=lambda e: e[0], reverse=True)
            useful = useful[:MAX_EQUIPMENT_OPTIONS]
            if not useful:
                return None
            gain = max(e[0] for e in useful)
            moved = max(e[1] for e in useful)
            none = QuestionOption(label="None of these", patch=Patch())
            question = question.model_copy(update={"options": [e[2] for e in useful] + [none]})
        else:
            if not effects:
                return None
            # Every answer is equally likely; the "no change" answers count as zero.
            options_counted = len(question.options)
            gain = sum(e[0] for e in effects) / options_counted
            moved = max(e[1] for e in effects)

        if gain < self._settings.question_min_gain:
            return None
        why = (
            f"Could change {moved} of your top suggestions"
            if moved
            else "Could change which dishes count as one step away"
        )
        return gain, question.model_copy(update={"why": why})

    def _signature(self, repertoire: list[UserDish], rule: DietRule, owned: Owned) -> _Signature:
        """Top-k suggestions and the one-step set for this kitchen."""
        top = self._graph.find_cousins(repertoire, self._settings.question_top_k, rule, owned)
        return _Signature(
            top=frozenset(d.id for d, _ in top),
            one_step=frozenset(self._graph.one_step_ids(repertoire, rule, owned)),
        )

    def _change(self, before: _Signature, after: _Signature) -> float:
        """0 (nothing moves) to 1 (everything does): half top suggestions, half one-step set."""
        k = max(1, self._settings.question_top_k)
        top_moved = len(before.top ^ after.top) / (2 * k)
        union = before.one_step | after.one_step
        one_step_moved = len(before.one_step ^ after.one_step) / len(union) if union else 0.0
        return 0.5 * top_moved + 0.5 * one_step_moved

    def _candidates(self, repertoire: list[UserDish], diet: Diet, have: Have) -> list[Question]:
        """Every question that could apply to this kitchen (scored later)."""
        candidates = [self._equipment_question(repertoire, have)]
        for i, dish in enumerate(repertoire):
            if dish.source != "described":
                continue  # a suggestion they cooked is a catalog dish; nothing to ask
            candidates.append(self._rice_question(i, dish))
            candidates.append(self._protein_question(i, dish, diet))
            candidates.extend(self._technique_questions(i, dish))
        return [c for c in candidates if c is not None]

    @staticmethod
    def _equipment_question(repertoire: list[UserDish], have: Have) -> Question | None:
        owned = {e for d in repertoire for e in d.equipment} | set(have.equipment)
        options = [
            QuestionOption(label=equipment_label(e), patch=Patch(add_equipment=[e]))
            for e in ASKABLE_EQUIPMENT
            if e not in owned
        ]
        if not options:
            return None
        return Question(
            id="kitchen:equipment",
            text="Which of these do you have in your kitchen?",
            multi=True,
            options=options,
            why="",
        )

    @staticmethod
    def _rice_question(i: int, dish: UserDish) -> Question | None:
        if dish.starch != "rice" or {"rice_in_stock", "plain_rice"} & set(dish.techniques):
            return None
        return Question(
            id=f"{_dish_key(dish)}:rice",
            about=dish.name,
            text="How do you cook the rice?",
            options=[
                QuestionOption(
                    label="In stock or broth", patch=Patch(dish=i, add_techniques=["rice_in_stock"])
                ),
                QuestionOption(
                    label="In plain water", patch=Patch(dish=i, add_techniques=["plain_rice"])
                ),
            ],
            why="",
        )

    @staticmethod
    def _protein_question(i: int, dish: UserDish, diet: Diet) -> Question | None:
        if dish.protein != "none" or dish.family not in PROTEIN_FAMILIES:
            return None
        options = [
            QuestionOption(label=label, patch=Patch(dish=i, protein=protein))
            for label, protein, allergen, meat in PROTEIN_CHOICES
            if not (meat and diet.vegetarian) and allergen not in diet.avoid
        ]
        options.append(QuestionOption(label="No, just as it is", patch=Patch()))
        return Question(
            id=f"{_dish_key(dish)}:protein",
            about=dish.name,
            text="Do you usually add a protein?",
            options=options,
            why="",
        )

    @staticmethod
    def _technique_questions(i: int, dish: UserDish) -> list[Question]:
        protein = PROTEIN_WORDS.get(dish.protein, "protein")
        return [
            Question(
                id=f"{_dish_key(dish)}:{q.technique}",
                about=dish.name,
                text=q.text.format(protein=protein),
                options=[
                    QuestionOption(label="Yes", patch=Patch(dish=i, add_techniques=[q.technique])),
                    QuestionOption(label="No", patch=Patch()),
                ],
                why="",
            )
            for q in TECHNIQUE_QUESTIONS
            if q.technique not in dish.techniques and q.applies(dish)
        ]


def _dish_key(dish: UserDish) -> str:
    """Stable id part for a dish: its name, lowercased and slugged."""
    return "".join(c if c.isalnum() else "_" for c in dish.name.lower()).strip("_")[:40]
