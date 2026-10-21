// Pure helpers for the user's kitchen: what they cook, plus what they've marked cooked.

import type { CookedDish } from "./storage";
import type { Cousin, Dish, UserDish } from "./types";

/** Most cooked dishes sent per request; the API accepts 30 dishes in total. */
export const MAX_COOKED_IN_REQUEST = 20;

/** A catalog dish the user has now cooked, as one of their own dishes. */
export function cookedToUserDish(dish: Dish): UserDish {
  return {
    name: dish.name,
    notes: "",
    matched_dish_id: dish.id,
    source: "cooked",
    family: dish.family,
    protein: dish.protein,
    starch: dish.starch,
    techniques: dish.techniques,
    equipment: dish.equipment,
    flavor: dish.flavor,
    key_ingredients: dish.key_ingredients,
    effort: dish.effort,
  };
}

/** Everything the user cooks: their own dishes, then the most recent cooked ones. */
export function repertoireOf(dishes: UserDish[], cooked: CookedDish[]): UserDish[] {
  const names = new Set(dishes.map((d) => d.name.toLowerCase()));
  const recent = [...cooked]
    .sort((a, b) => b.cookedAt.localeCompare(a.cookedAt))
    .filter((c) => !names.has(c.name.toLowerCase()))
    .slice(0, MAX_COOKED_IN_REQUEST)
    .map((c) => c.dish);
  return [...dishes, ...recent];
}

/**
 * Ingredients the current suggestions need (and can't swap): most common first, then in
 * the order the suggestions are ranked — so the top picks' needs come before obscure ones.
 */
export function oftenNeeded(cousins: Cousin[], limit = 8): string[] {
  const counts = new Map<string, { n: number; first: number }>();
  let order = 0;
  for (const { delta } of cousins) {
    const swapped = new Set((delta.swaps ?? []).map((s) => s.need));
    for (const item of delta.new_ingredients) {
      if (swapped.has(item)) continue;
      const seen = counts.get(item);
      counts.set(item, seen ? { ...seen, n: seen.n + 1 } : { n: 1, first: order++ });
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1].n - a[1].n || a[1].first - b[1].first)
    .slice(0, limit)
    .map(([item]) => item);
}

/** Equipment the user's own dishes already use. */
export function impliedEquipment(dishes: UserDish[]): string[] {
  return [...new Set(dishes.flatMap((d) => d.equipment))];
}
