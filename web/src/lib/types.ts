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
  source?: "described" | "cooked";
  /** Ingredients the app guessed from a vague phrase ("Indian spices"); shown to confirm. */
  assumed_ingredients?: string[];
}

/** What the user has beyond what their dishes imply. */
export interface Have {
  equipment: string[];
  ingredients: string[];
}

/** What an answer to a follow-up question changes. */
export interface Patch {
  dish: number | null;
  add_techniques: string[];
  protein: string | null;
  add_equipment: string[];
}

export interface QuestionOption {
  label: string;
  patch: Patch;
}

export interface Question {
  id: string;
  /** The user's dish it's about; null = the kitchen. */
  about: string | null;
  text: string;
  multi: boolean;
  options: QuestionOption[];
  why: string;
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

export type Allergen =
  | "dairy"
  | "egg"
  | "gluten"
  | "peanut"
  | "tree_nut"
  | "soy"
  | "fish"
  | "shellfish"
  | "sesame";

export interface Diet {
  vegetarian: boolean;
  avoid: Allergen[];
}

export interface TonightPicks {
  familiar: UserDish | null;
  one_step: Cousin | null;
  stretch: Cousin | null;
}

export interface MapCousin {
  dish: Dish;
  delta: Delta;
}

export interface KitchenMap {
  kitchen: UserDish[];
  cousins: MapCousin[];
  one_step_count: number;
  catalog_size: number;
}

export interface SharedKitchen {
  dishes: UserDish[];
  created_at: string;
}

export interface EvalCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface EvalCase {
  id: string;
  checks: EvalCheck[];
  sample?: DiffText;
  cousins?: string[];
}

export interface EvalSuite {
  passed: number;
  total: number;
  results: EvalCase[];
}

export interface EvalResults {
  model: string;
  run_at: string;
  passed: number;
  total: number;
  pass_rate: number;
  suites: Record<string, EvalSuite>;
}
