// Common home dishes shown as photo tiles on the start page. They're catalog dishes,
// so picking them needs no AI call. Data copied from api/data/dishes.json (a few names
// shortened to fit a tile).

import dishes from "./starter-dishes.json";
import type { Dish, UserDish } from "./types";

export const STARTER_DISHES = dishes as Dish[];

/** A tapped tile, as one of the user's own dishes. */
export function pickedToUserDish(dish: Dish): UserDish {
  return {
    name: dish.name,
    notes: "",
    matched_dish_id: dish.id,
    source: "described",
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

export function startersById(ids: string[]): Dish[] {
  return STARTER_DISHES.filter((d) => ids.includes(d.id));
}
