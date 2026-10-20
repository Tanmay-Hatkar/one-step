"""The dish graph: how far is a catalog dish from what the user already cooks?

This is the heart of One Step and it is deliberately plain code, not an LLM call:
distance is a weighted comparison of structural parts (family, techniques,
equipment, ingredients). The LLM only writes up the result.
"""

import logging
from collections import Counter
from dataclasses import dataclass

from app.config import Settings
from app.models.dish import Delta, Dish, UserDish
from app.services.ingredients import missing_ingredients, normalize, pantry_of

logger = logging.getLogger(__name__)

# Everyone is assumed to have a stovetop; it never counts as new equipment.
ASSUMED_EQUIPMENT: frozenset[str] = frozenset({"stovetop"})

# Everyday techniques any home cook already does. They still show up in the delta,
# but they never count as a "new skill" and barely move the score.
BASIC_TECHNIQUES: frozenset[str] = frozenset({"sear", "pan_fry", "simmer", "boil", "plain_rice"})


@dataclass(frozen=True)
class ScoreWeights:
    """How much each kind of similarity or difference moves the score."""

    same_family: float = 3.0
    shared_technique: float = 1.0
    new_technique: float = -1.5
    new_basic_technique: float = -0.2
    dropped_technique: float = -0.5
    same_protein: float = 1.5
    same_starch: float = 1.5
    shared_flavor: float = 0.3
    new_ingredient: float = -0.35
    new_equipment: float = -2.5
    one_step_bonus: float = 2.0


class GraphService:
    """Finds and ranks 'cousin' dishes relative to a user's repertoire."""

    def __init__(
        self, dishes: list[Dish], settings: Settings, weights: ScoreWeights | None = None
    ) -> None:
        """Create the service.

        Args:
            dishes: The full catalog.
            settings: App settings (one-step thresholds, diversity caps).
            weights: Optional scoring weights override (used by tests and tuning).
        """
        self._dishes = dishes
        self._settings = settings
        self._w = weights or ScoreWeights()

    def compute_delta(
        self, anchor: UserDish, dish: Dish, pantry: set[str], equipment: set[str]
    ) -> Delta:
        """Compute what changes between one user dish and one catalog dish.

        Args:
            anchor: A dish the user cooks.
            dish: A catalog dish.
            pantry: Normalized ingredients the user has (across their repertoire).
            equipment: Equipment the user has (across their repertoire).

        Returns:
            The structured difference, with a closeness score.
        """
        anchor_tech, dish_tech = set(anchor.techniques), set(dish.techniques)
        shared = [t for t in dish.techniques if t in anchor_tech]
        new_tech = [t for t in dish.techniques if t not in anchor_tech]
        dropped = [t for t in anchor.techniques if t not in dish_tech]
        new_equipment = [
            e for e in dish.equipment if e not in equipment and e not in ASSUMED_EQUIPMENT
        ]
        new_ingredients = missing_ingredients(dish.key_ingredients, pantry)
        new_flavors = [f for f in dish.flavor if f not in anchor.flavor]
        shared_flavors = len(dish.flavor) - len(new_flavors)
        new_skills = [t for t in new_tech if t not in BASIC_TECHNIQUES]
        is_one_step = (
            len(new_skills) <= self._settings.one_step_max_new_techniques
            and not new_equipment
            and len(new_ingredients) <= self._settings.one_step_max_new_ingredients
        )

        same_family = anchor.family == dish.family
        same_protein = anchor.protein == dish.protein
        same_starch = anchor.starch == dish.starch
        w = self._w
        score = (
            w.same_family * same_family
            + w.shared_technique * len(shared)
            + w.new_technique * len(new_skills)
            + w.new_basic_technique * (len(new_tech) - len(new_skills))
            + w.dropped_technique * len(dropped)
            + w.same_protein * same_protein
            + w.same_starch * same_starch
            + w.shared_flavor * shared_flavors
            + w.new_ingredient * len(new_ingredients)
            + w.new_equipment * len(new_equipment)
            + w.one_step_bonus * is_one_step
        )
        return Delta(
            anchor_name=anchor.name,
            shared_techniques=shared,
            new_techniques=new_tech,
            dropped_techniques=dropped,
            new_equipment=new_equipment,
            new_ingredients=new_ingredients,
            new_flavors=new_flavors,
            same_protein=same_protein,
            same_starch=same_starch,
            same_family=same_family,
            score=round(score, 2),
            is_one_step=is_one_step,
        )

    def find_cousins(self, repertoire: list[UserDish], limit: int) -> list[tuple[Dish, Delta]]:
        """Return the closest catalog dishes the user doesn't already cook.

        Each candidate is anchored to whichever of the user's dishes it's closest to.
        Ranked by score (one-step dishes get a bonus, not absolute priority), with at
        most `max_cousins_per_region` per region so the list actually travels.

        Args:
            repertoire: The user's dishes.
            limit: How many cousins to return.

        Returns:
            (dish, delta) pairs, best first.
        """
        if not repertoire:
            return []
        pantry = pantry_of([d.key_ingredients for d in repertoire])
        equipment = {e for d in repertoire for e in d.equipment}
        known = self._known_ids(repertoire)

        scored: list[tuple[Dish, Delta]] = []
        for dish in self._dishes:
            if dish.id in known:
                continue
            best = max(
                (self.compute_delta(a, dish, pantry, equipment) for a in repertoire),
                key=lambda d: d.score,
            )
            if self._is_new_enough(best):
                scored.append((dish, best))

        scored.sort(key=lambda pair: pair[1].score, reverse=True)
        return self._diversify(scored, limit)

    def _known_ids(self, repertoire: list[UserDish]) -> set[str]:
        """Catalog ids the user already cooks (matched by id or by name)."""
        names = {normalize(d.name) for d in repertoire}
        ids = {d.matched_dish_id for d in repertoire if d.matched_dish_id}
        ids.update(d.id for d in self._dishes if normalize(d.name) in names)
        return ids

    @staticmethod
    def _is_new_enough(delta: Delta) -> bool:
        """A cousin must change *something*; otherwise it's the same dish renamed."""
        return bool(delta.new_techniques or delta.new_ingredients or delta.new_flavors)

    def _diversify(self, scored: list[tuple[Dish, Delta]], limit: int) -> list[tuple[Dish, Delta]]:
        """Take the best candidates while capping how many come from one region."""
        per_region: Counter[str] = Counter()
        picked: list[tuple[Dish, Delta]] = []
        for dish, delta in scored:
            if per_region[dish.region] >= self._settings.max_cousins_per_region:
                continue
            per_region[dish.region] += 1
            picked.append((dish, delta))
            if len(picked) == limit:
                break
        return picked
