// Per-device convenience only: remembers your kitchen on this browser (no accounts yet).
// Every access is guarded — storage can be blocked, full, or unavailable.

import type { Cousin, Diet, UserDish } from "./types";

const KEY = "one-step:v2";
const LEGACY_KEY = "one-step:v1";

/** A catalog dish the user marked "I cooked this". It joins their kitchen. */
export interface CookedDish {
  id: string;
  name: string;
  cookedAt: string;
  dish: UserDish;
}

export interface Prefs {
  diet: Diet;
  /** Time available tonight in minutes; null means any. */
  minutes: number | null;
}

export interface SavedKitchen {
  text: string;
  dishes: UserDish[];
  cooked: CookedDish[];
  prefs: Prefs;
  cousins: Cousin[];
}

export const DEFAULT_PREFS: Prefs = { diet: { vegetarian: false, avoid: [] }, minutes: null };

export function loadKitchen(): SavedKitchen | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) return { ...emptyKitchen(), ...(JSON.parse(raw) as Partial<SavedKitchen>) };
    const legacy = window.localStorage.getItem(LEGACY_KEY);
    if (legacy) return { ...emptyKitchen(), ...(JSON.parse(legacy) as Partial<SavedKitchen>) };
    return null;
  } catch {
    return null;
  }
}

export function saveKitchen(kitchen: SavedKitchen): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(kitchen));
  } catch {
    // Storage unavailable — the app still works, it just won't remember.
  }
}

export function emptyKitchen(): SavedKitchen {
  return { text: "", dishes: [], cooked: [], prefs: DEFAULT_PREFS, cousins: [] };
}
