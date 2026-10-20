"""The dish graph: how far is a catalog dish from what the user already cooks?

This is the heart of One Step and it is deliberately plain code, not an LLM call:
distance is a weighted comparison of structural parts (family, techniques,
equipment, ingredients). The LLM only writes up the result.
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from app.config import Settings
from app.models.dish import Delta, Dish, UserDish
from app.services.diet import allows, user_dish_allows
from app.services.ingredients import missing_ingredients, normalize, pantry_of

logger = logging.getLogger(__name__)

# Everyone is assumed to have a stovetop; it never counts as new equipment.
ASSUMED_EQUIPMENT: frozenset[str] = frozenset({"stovetop"})

# Everyday techniques any home cook already does. They still show up in the delta,
# but they never count as a "new skill" and barely move the score.
BASIC_TECHNIQUES: frozenset[str] = frozenset({"sear", "pan_fry", "simmer", "boil", "plain_rice"})

# At or under this many minutes, tonight's familiar pick prefers weeknight dishes.
QUICK_NIGHT_MINUTES = 60


@dataclass(frozen=True)
class DietRule:
    """Hard diet rule applied to every candidate. Empty = no restriction."""

    vegetarian: bool = False
    avoid: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TonightPicks:
    """Three ways to go tonight; any may be None when nothing fits."""

    familiar: UserDish | None
    one_step: tuple[Dish, Delta] | None
    stretch: tuple[Dish, Delta] | None


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

    @property
    def catalog_size(self) -> int:
        """How many dishes are in the catalog."""
        return len(self._dishes)

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
        same_family = anchor.family == dish.family
        same_protein = anchor.protein == dish.protein
        same_starch = anchor.starch == dish.starch
        # Swapping the main protein (chicken → lamb) is a real change, not one step.
        protein_swap = not same_protein and "none" not in (anchor.protein, dish.protein)
        # One step keeps the base: the same kind of dish or the same starch (rice ≠ pasta).
        keeps_base = same_family or same_starch
        is_one_step = (
            len(new_skills) <= self._settings.one_step_max_new_techniques
            and not new_equipment
            and len(new_ingredients) <= self._settings.one_step_max_new_ingredients
            and not protein_swap
            and keeps_base
        )

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

    def find_cousins(
        self, repertoire: list[UserDish], limit: int, diet: DietRule | None = None
    ) -> list[tuple[Dish, Delta]]:
        """Return the closest catalog dishes the user doesn't already cook.

        Each candidate is anchored to whichever of the user's dishes it's closest to.
        Ranked by score (one-step dishes get a bonus, not absolute priority), with at
        most `max_cousins_per_region` per region so the list actually travels.

        Args:
            repertoire: The user's dishes.
            limit: How many cousins to return.
            diet: Hard diet rule; dishes that break it are never returned.

        Returns:
            (dish, delta) pairs, best first.
        """
        return self._diversify(self._ranked(repertoire, diet or DietRule()), limit)

    def pick_tonight(
        self,
        repertoire: list[UserDish],
        diet: DietRule | None = None,
        max_minutes: int | None = None,
        skip: frozenset[str] = frozenset(),
        today: date | None = None,
    ) -> TonightPicks:
        """Pick a familiar dish, a one-step dish and a stretch for tonight.

        Args:
            repertoire: The user's dishes.
            diet: Hard diet rule.
            max_minutes: Time available tonight; None means any.
            skip: Catalog ids and user dish names the user said 'not tonight' to.
            today: Used to rotate the familiar pick day by day (defaults to today).

        Returns:
            The three picks; any is None when nothing fits.
        """
        diet = diet or DietRule()
        fits = [
            (dish, delta)
            for dish, delta in self._ranked(repertoire, diet)
            if dish.id not in skip and (max_minutes is None or dish.time_minutes <= max_minutes)
        ]
        one_step = next(((d, x) for d, x in fits if x.is_one_step), None)
        stretch_pool = [
            (d, x)
            for d, x in fits
            if not x.is_one_step
            and not x.new_equipment
            and len(self._new_skills(x)) <= self._settings.stretch_max_new_techniques
        ]
        if one_step:
            # Prefer a stretch from a different region than the one-step pick.
            other = [p for p in stretch_pool if p[0].region != one_step[0].region]
            stretch_pool = other or stretch_pool
        stretch = stretch_pool[0] if stretch_pool else None
        familiar = self._familiar(repertoire, diet, max_minutes, skip, today or date.today())
        return TonightPicks(familiar=familiar, one_step=one_step, stretch=stretch)

    def _ranked(self, repertoire: list[UserDish], diet: DietRule) -> list[tuple[Dish, Delta]]:
        """Every allowed, genuinely new catalog dish with its best delta, best first."""
        if not repertoire:
            return []
        pantry = pantry_of([d.key_ingredients for d in repertoire])
        equipment = {e for d in repertoire for e in d.equipment}
        known = self._known_ids(repertoire)

        scored: list[tuple[Dish, Delta]] = []
        for dish in self._dishes:
            if dish.id in known or not allows(dish, diet.vegetarian, diet.avoid):
                continue
            best = self._best_delta(repertoire, dish, pantry, equipment)
            if self._is_new_enough(best):
                scored.append((dish, best))

        scored.sort(key=lambda pair: pair[1].score, reverse=True)
        return scored

    def neighbourhood(
        self, repertoire: list[UserDish], diet: DietRule | None = None
    ) -> tuple[list[tuple[Dish, Delta]], int]:
        """The map: each of the user's dishes with its closest cousins.

        Every candidate is attached to its best anchor; each anchor keeps its
        `map_cousins_per_dish` closest, capped at `map_max_cousins` overall.

        Args:
            repertoire: The user's dishes.
            diet: Hard diet rule.

        Returns:
            (cousins best first, how many catalog dishes are one step away).
        """
        ranked = self._ranked(repertoire, diet or DietRule())
        per_anchor: Counter[str] = Counter()
        picked: list[tuple[Dish, Delta]] = []
        for dish, delta in ranked:
            if per_anchor[delta.anchor_name] >= self._settings.map_cousins_per_dish:
                continue
            per_anchor[delta.anchor_name] += 1
            picked.append((dish, delta))
            if len(picked) == self._settings.map_max_cousins:
                break
        return picked, sum(1 for _, d in ranked if d.is_one_step)

    def cousin_for(
        self, repertoire: list[UserDish], dish_id: str, diet: DietRule | None = None
    ) -> tuple[Dish, Delta] | None:
        """One specific catalog dish relative to the user's kitchen (a tap on the map).

        Args:
            repertoire: The user's dishes.
            dish_id: Catalog id.
            diet: Hard diet rule.

        Returns:
            (dish, delta), or None if unknown, already cooked, or not allowed by the diet.
        """
        diet = diet or DietRule()
        dish = next((d for d in self._dishes if d.id == dish_id), None)
        if (
            dish is None
            or not repertoire
            or dish.id in self._known_ids(repertoire)
            or not allows(dish, diet.vegetarian, diet.avoid)
        ):
            return None
        pantry = pantry_of([d.key_ingredients for d in repertoire])
        equipment = {e for d in repertoire for e in d.equipment}
        return dish, self._best_delta(repertoire, dish, pantry, equipment)

    def _best_delta(
        self, repertoire: list[UserDish], dish: Dish, pantry: set[str], equipment: set[str]
    ) -> Delta:
        """The delta against whichever of the user's dishes this one should be compared to."""
        return max(
            (
                (self.compute_delta(a, dish, pantry, equipment), a.source == "described")
                for a in repertoire
            ),
            key=self._anchor_preference,
        )[0]

    @staticmethod
    def _anchor_preference(pair: tuple[Delta, bool]) -> tuple[bool, bool, float]:
        """Which of the user's dishes to compare a candidate against.

        One step away beats not; then the user's own described dishes beat ones they've
        cooked from a suggestion (so "your chicken leg with rice, but…" reads naturally
        and a cooked dish only anchors what it newly unlocks); then the closer score.
        """
        delta, described = pair
        return (delta.is_one_step, described, delta.score)

    @staticmethod
    def _familiar(
        repertoire: list[UserDish],
        diet: DietRule,
        max_minutes: int | None,
        skip: frozenset[str],
        today: date,
    ) -> UserDish | None:
        """One of the user's own dishes, rotating daily; quick ones on short nights."""
        options = [
            d
            for d in repertoire
            if d.name not in skip and user_dish_allows(d, diet.vegetarian, diet.avoid)
        ]
        if max_minutes is not None and max_minutes <= QUICK_NIGHT_MINUTES:
            options = [d for d in options if d.effort == "weeknight"] or options
        if not options:
            return None
        return options[today.toordinal() % len(options)]

    @staticmethod
    def _new_skills(delta: Delta) -> list[str]:
        """New techniques that aren't everyday basics."""
        return [t for t in delta.new_techniques if t not in BASIC_TECHNIQUES]

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
