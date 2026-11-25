// Remembers your kitchen on this browser; if you've signed in with a passkey, each save is
// also synced to your account. Every access is guarded — storage can be blocked or full.

import { queueSync } from "./account";
import type { SavedDish } from "./saved";
import type { Cousin, Diet, Have, Pasted, UserDish } from "./types";

const KEY = "one-step:v2";
const LEGACY_KEY = "one-step:v1";

/** A catalog dish the user marked "I cooked this". It joins their kitchen. */
export interface CookedDish {
  id: string;
  name: string;
  cookedAt: string;
  dish: UserDish;
}

/** A recipe the user pasted from somewhere, with its write-up from their kitchen. */
export interface PastedEntry extends Pasted {
  pastedAt: string;
  /** True when it was read from a screenshot or photo rather than text or a link. */
  fromPhoto?: boolean;
}

/** One time the user cooked one of their dishes (by the name it has in their kitchen). */
export interface CookLogEntry {
  name: string;
  at: string;
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
  /** Dishes saved for later, newest first. */
  saved: SavedDish[];
  /** Shopping-list items already bought. */
  bought: string[];
  /** Recipes pasted from elsewhere, newest first. */
  pasted: PastedEntry[];
  /** What was cooked and when, newest first. Drives "you haven't made this in a while". */
  log: CookLogEntry[];
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
    saved: [],
    bought: [],
    pasted: [],
    log: [],
  };
}
