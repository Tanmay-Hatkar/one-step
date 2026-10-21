// Readable names for vocabulary ids. Mirrors api/app/models/labels.py.

import type { Allergen } from "./types";

const TECHNIQUES: Record<string, string> = {
  marinate: "marinating",
  spice_paste: "spice paste",
  temper_spices: "blooming whole spices",
  sear: "searing",
  pan_fry: "pan-frying",
  stir_fry: "stir-frying",
  deep_fry: "deep-frying",
  roast: "roasting",
  grill: "grilling",
  braise: "braising",
  simmer: "simmering",
  steam: "steaming",
  boil: "boiling",
  bake: "baking",
  rice_in_stock: "rice cooked in stock",
  plain_rice: "plain rice",
  layered_dum: "layering and slow-steaming",
  scramble: "scrambling",
  knead_dough: "kneading dough",
  wrap_and_roll: "wrapping",
  poach: "poaching",
  blend_puree: "blending a sauce",
};

export function techniqueLabel(id: string): string {
  return TECHNIQUES[id] ?? id.replaceAll("_", " ");
}

export function equipmentLabel(id: string): string {
  return id.replaceAll("_", " ");
}

/** Every equipment id, in the order a home cook is most likely to have it. */
export const EQUIPMENT: { id: string; label: string }[] = [
  { id: "stovetop", label: "Stovetop" },
  { id: "oven", label: "Oven" },
  { id: "pressure_cooker", label: "Pressure cooker" },
  { id: "rice_cooker", label: "Rice cooker" },
  { id: "blender", label: "Blender or mixer" },
  { id: "wok", label: "Wok" },
  { id: "air_fryer", label: "Air fryer" },
  { id: "griddle", label: "Griddle or tawa" },
  { id: "grill", label: "Grill or tandoor" },
  { id: "steamer", label: "Steamer" },
];

/** Everyday techniques that never count as a new skill. Mirrors BASIC_TECHNIQUES in the API. */
export const BASIC_TECHNIQUES = new Set(["sear", "pan_fry", "simmer", "boil", "plain_rice"]);

export const ALLERGENS: { id: Allergen; label: string }[] = [
  { id: "dairy", label: "Dairy" },
  { id: "egg", label: "Eggs" },
  { id: "gluten", label: "Gluten" },
  { id: "peanut", label: "Peanuts" },
  { id: "tree_nut", label: "Tree nuts" },
  { id: "soy", label: "Soy" },
  { id: "fish", label: "Fish" },
  { id: "shellfish", label: "Shellfish" },
  { id: "sesame", label: "Sesame" },
];

export function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

/** 75 → "1:15" */
export function formatClock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
