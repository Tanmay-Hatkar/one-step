// Light, dark, or follow the system. Kept on this device; applied as data-theme on <html>
// (no attribute means "system"). theme-script.ts applies it before first paint, so no flash.

import { useCallback, useSyncExternalStore } from "react";

export type Theme = "system" | "light" | "dark";

import { THEME_KEY } from "./theme-script";

const EVENT = "one-step:theme";

function read(): Theme {
  try {
    const t = window.localStorage.getItem(THEME_KEY);
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  return () => window.removeEventListener(EVENT, onChange);
}

/** The chosen theme and a setter that applies and remembers it. */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const theme = useSyncExternalStore(subscribe, read, () => "system" as Theme);
  const setTheme = useCallback((next: Theme) => {
    const root = document.documentElement;
    if (next === "system") delete root.dataset.theme;
    else root.dataset.theme = next;
    try {
      if (next === "system") window.localStorage.removeItem(THEME_KEY);
      else window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Not remembered; it still applies for this visit.
    }
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return [theme, setTheme];
}
