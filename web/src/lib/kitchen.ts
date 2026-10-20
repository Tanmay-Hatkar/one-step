// Pure helpers for the user's kitchen: what they cook, plus what they've marked cooked.

import type { CookedDish } from "./storage";
import type { Dish, UserDish } from "./types";

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
