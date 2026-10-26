// Remembers your kitchen on this browser; if you've signed in with a passkey, each save is
// also synced to your account. Every access is guarded — storage can be blocked or full.

import { queueSync } from "./account";
import type { Cousin, Diet, Have, UserDish } from "./types";

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
  /** Equipment and pantry beyond what their dishes imply. */
  have: Have;
}

export interface SavedKitchen {
  text: string;
  dishes: UserDish[];
  cooked: CookedDish[];
  prefs: Prefs;
  cousins: Cousin[];
  /** Follow-up questions already answered, so they aren't asked again. */
  dismissed: string[];
  /** Photo tiles tapped on the start page (catalog dish ids). */
  picked: string[];
}

export const EMPTY_HAVE: Have = { equipment: [], ingredients: [] };

export const DEFAULT_PREFS: Prefs = {
  diet: { vegetarian: false, avoid: [] },
  minutes: null,
  have: EMPTY_HAVE,
};

export function loadKitchen(): SavedKitchen | null {
  try {
    const raw =
      window.localStorage.getItem(KEY) ??
      window.localStorage.getItem(LEGACY_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as Partial<SavedKitchen>;
    // Fill in anything older versions didn't save.
    const prefs = { ...DEFAULT_PREFS, ...saved.prefs };
    return {
      ...emptyKitchen(),
      ...saved,
      prefs: { ...prefs, have: { ...EMPTY_HAVE, ...prefs.have } },
    };
  } catch {
    return null;
  }
}

export function saveKitchen(kitchen: SavedKitchen, { sync = true } = {}): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(kitchen));
  } catch {
    // Storage unavailable — the app still works, it just won't remember.
  }
  if (sync) queueSync(kitchen);
}

export function emptyKitchen(): SavedKitchen {
  return {
    text: "",
    dishes: [],
    cooked: [],
    prefs: DEFAULT_PREFS,
    cousins: [],
    dismissed: [],
    picked: [],
  };
}
