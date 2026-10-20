// Per-device convenience only: remembers your last kitchen on this browser.
// Every access is guarded — storage can be blocked, full, or unavailable.

const KEY = "one-step:v1";

export interface SavedKitchen {
  text: string;
  dishes: import("./types").UserDish[];
  cousins: import("./types").Cousin[];
}

export function loadKitchen(): SavedKitchen | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SavedKitchen) : null;
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

export function clearKitchen(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // Nothing to do.
  }
}
