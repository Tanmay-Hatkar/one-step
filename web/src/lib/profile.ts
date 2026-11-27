// The name the app greets you by. Optional, kept on this device only (never sent to the
// server or synced), and every storage access is guarded.

import { useCallback, useSyncExternalStore } from "react";

import { track } from "./track";

const NAME_KEY = "one-step:name";
const EVENT = "one-step:name";
export const MAX_NAME_CHARS = 30;

function read(): string {
  try {
    return window.localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** Clean up what was typed: trimmed, single spaces, capped. */
export function cleanName(raw: string): string {
  return raw.replace(/\s+/g, " ").trim().slice(0, MAX_NAME_CHARS);
}

/** The saved name ("" when none, and on the server) and a setter that saves it. */
export function useName(): [string, (name: string) => void] {
  const name = useSyncExternalStore(subscribe, read, () => "");
  const setName = useCallback((next: string) => {
    try {
      const clean = cleanName(next);
      if (clean && !read()) track("name_set"); // only that a name was given, never the name
      if (clean) window.localStorage.setItem(NAME_KEY, clean);
      else window.localStorage.removeItem(NAME_KEY);
    } catch {
      // Storage blocked: the greeting just stays generic.
    }
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return [name, setName];
}

/** "morning" | "afternoon" | "evening" for an hour of the day (0–23). */
export function partOfDay(hour: number): "morning" | "afternoon" | "evening" {
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 17) return "afternoon";
  return "evening";
}
