// Anonymous usage counts: a random id for this browser and a fixed list of event names.
// No text you type, no IP, no account. Batched and sent a moment later; failures are dropped.

import { request } from "./api";

const DEVICE_KEY = "one-step:device";
const FLUSH_MS = 2000;
const MAX_BATCH = 20;

export type EventName =
  | "landed"
  | "kitchen_built"
  | "results_shown"
  | "name_set"
  | "dish_opened"
  | "cooked"
  | "saved"
  | "cook_mode"
  | "shopping_shared"
  | "installed"
  | "pasted";

const queue: { name: EventName; dish_id?: string }[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

function deviceId(): string | null {
  try {
    let id = window.localStorage.getItem(DEVICE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      window.localStorage.setItem(DEVICE_KEY, id);
    }
    return id;
  } catch {
    return null; // storage blocked: don't count this browser at all
  }
}

function flush() {
  timer = null;
  const device = deviceId();
  const events = queue.splice(0, MAX_BATCH);
  if (!device || !events.length) return;
  request("/api/events", {
    method: "POST",
    body: JSON.stringify({ device, events }),
    keepalive: true,
  }).catch(() => {});
  if (queue.length) timer = setTimeout(flush, FLUSH_MS);
}

/** Count that something happened (optionally to a catalog dish). */
export function track(name: EventName, dishId?: string): void {
  if (typeof window === "undefined") return;
  queue.push(dishId ? { name, dish_id: dishId } : { name });
  if (!timer) timer = setTimeout(flush, FLUSH_MS);
}

/** Count something at most once per browser session (e.g. a visit, not every page). */
export function trackOnce(name: EventName): void {
  if (typeof window === "undefined") return;
  const key = `one-step:once:${name}`;
  try {
    if (window.sessionStorage.getItem(key)) return;
    window.sessionStorage.setItem(key, "1");
  } catch {
    return; // storage blocked: can't tell repeats apart, so don't count
  }
  track(name);
}

/** Send a message from the feedback box. */
export function sendFeedback(message: string): Promise<void> {
  return request("/api/feedback", {
    method: "POST",
    body: JSON.stringify({ message, page: window.location.pathname }),
  });
}
