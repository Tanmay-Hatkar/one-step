// Mirrors the API's Pydantic models (api/app/models). Keep in sync.

export type Effort = "weeknight" | "weekend";

export interface DishParts {
  family: string;
  protein: string;
  starch: string;
  techniques: string[];
  equipment: string[];
  flavor: string[];
  key_ingredients: string[];
  effort: Effort;
}

export interface UserDish extends DishParts {
  name: string;
  notes: string;
  matched_dish_id: string | null;
}

export interface Dish extends DishParts {
  id: string;
  name: string;
  cuisine: string;
  region: string;
  time_minutes: number;
  allergens: string[];
  vegetarian: boolean;
  summary: string;
}

export interface Delta {
  anchor_name: string;
  shared_techniques: string[];
  new_techniques: string[];
  dropped_techniques: string[];
  new_equipment: string[];
  new_ingredients: string[];
  new_flavors: string[];
  same_protein: boolean;
  same_starch: boolean;
  same_family: boolean;
  score: number;
  is_one_step: boolean;
}

export interface DiffText {
  headline: string;
  changes: string[];
  keep_line: string;
}

export interface Cousin {
  dish: Dish;
  delta: Delta;
  diff: DiffText;
}

export interface DishStats {
  dishes: number;
  regions: number;
}
