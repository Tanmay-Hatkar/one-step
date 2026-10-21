"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, findCousins, getTonight, parseRepertoire } from "./api";
import { cookedToUserDish, repertoireOf } from "./kitchen";
import {
  type CookedDish,
  DEFAULT_PREFS,
  type Prefs,
  loadKitchen,
  saveKitchen,
} from "./storage";
import type { Cousin, Dish, Have, TonightPicks, UserDish } from "./types";

export type Phase = "input" | "reading" | "confirm" | "finding" | "results";

/** Wait this long after the last preference change before asking the API again. */
const PREFS_DEBOUNCE_MS = 400;

export interface CookedNotice {
  id: string;
  name: string;
}

function messageOf(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong.";
}

/** All state for the kitchen page, its API calls, and what's remembered on this device. */
export function useKitchen() {
  const [phase, setPhase] = useState<Phase>("input");
  const [text, setText] = useState("");
  const [dishes, setDishes] = useState<UserDish[]>([]);
  const [cooked, setCooked] = useState<CookedDish[]>([]);
  const [prefs, setPrefsState] = useState<Prefs>(DEFAULT_PREFS);
  const [cousins, setCousins] = useState<Cousin[]>([]);
  const [tonight, setTonight] = useState<TonightPicks | null>(null);
  const [skip, setSkip] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [notice, setNotice] = useState<CookedNotice | null>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);

  // Only the latest request may update the page (preferences can change mid-flight).
  const requestId = useRef(0);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Answered questions are remembered alongside everything else.
  const dismissedRef = useRef<string[]>([]);
  const persist = useCallback(
    (next: { text: string; dishes: UserDish[]; cooked: CookedDish[]; prefs: Prefs; cousins: Cousin[] }) =>
      saveKitchen({ ...next, dismissed: dismissedRef.current }),
    [],
  );

  /** Fetch cousins and tonight's picks for a kitchen; returns the cousins, or null if stale. */
  const fetchAll = useCallback(
    async (own: UserDish[], done: CookedDish[], p: Prefs, skipped: string[]) => {
      const id = ++requestId.current;
      const repertoire = repertoireOf(own, done);
      const [found, picks] = await Promise.all([
        findCousins(repertoire, p.diet, p.have),
        getTonight(repertoire, p.diet, p.have, p.minutes, skipped),
      ]);
      if (id !== requestId.current) return null;
      setCousins(found);
      setTonight(picks);
      return found;
    },
    [],
  );

  /** Re-fetch after a change on the results page, keeping the current results visible. */
  const refresh = useCallback(
    async (own: UserDish[], done: CookedDish[], p: Prefs, skipped: string[], t: string) => {
      setUpdating(true);
      setError(null);
      try {
        const found = await fetchAll(own, done, p, skipped);
        if (found) persist({ text: t, dishes: own, cooked: done, prefs: p, cousins: found });
      } catch (err) {
        setError(messageOf(err));
      } finally {
        setUpdating(false);
      }
    },
    [fetchAll, persist],
  );

  useEffect(() => {
    // Restoring from localStorage must happen after hydration, in an effect.
    const saved = loadKitchen();
    if (!saved) return;
    /* eslint-disable react-hooks/set-state-in-effect */
    setText(saved.text);
    setDishes(saved.dishes);
    setCooked(saved.cooked);
    setPrefsState(saved.prefs);
    setDismissed(saved.dismissed);
    dismissedRef.current = saved.dismissed;
    if (saved.dishes.length && !saved.cousins.length) {
      setPhase("confirm"); // they left while checking what was heard
    } else if (saved.dishes.length) {
      setCousins(saved.cousins);
      setPhase("results");
      void refresh(saved.dishes, saved.cooked, saved.prefs, [], saved.text);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [refresh]);

  async function submit() {
    const input = text.trim();
    if (input.length < 3) {
      setError("Tell me about a dish or two you cook.");
      return;
    }
    setError(null);
    setSkip([]);
    try {
      setPhase("reading");
      const parsed = await parseRepertoire(input);
      setDishes(parsed);
      setCousins([]);
      setTonight(null);
      // Show what was understood before searching, so guesses can be fixed first.
      setPhase("confirm");
      persist({ text: input, dishes: parsed, cooked, prefs, cousins: [] });
    } catch (err) {
      setError(messageOf(err));
      setPhase("input");
    }
  }

  /** Accept the checked kitchen (and any answers), then find dishes. */
  async function confirmKitchen(checked: UserDish[], have: Have, answered: string[]) {
    const nextPrefs = { ...prefs, have };
    const nextDismissed = [...new Set([...dismissed, ...answered])];
    dismissedRef.current = nextDismissed;
    setDismissed(nextDismissed);
    setDishes(checked);
    setPrefsState(nextPrefs);
    setError(null);
    setSkip([]);
    setPhase("finding");
    try {
      const found = await fetchAll(checked, cooked, nextPrefs, []);
      setPhase("results");
      if (found) persist({ text, dishes: checked, cooked, prefs: nextPrefs, cousins: found });
    } catch (err) {
      setError(messageOf(err));
      setPhase("confirm");
    }
  }

  function setPrefs(next: Prefs) {
    setPrefsState(next);
    if (phase !== "results") {
      persist({ text, dishes, cooked, prefs: next, cousins });
      return;
    }
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      void refresh(dishes, cooked, next, skip, text);
    }, PREFS_DEBOUNCE_MS);
  }

  function markCooked(dish: Dish) {
    if (cooked.some((c) => c.id === dish.id)) return;
    const next = [
      ...cooked,
      { id: dish.id, name: dish.name, cookedAt: new Date().toISOString(), dish: cookedToUserDish(dish) },
    ];
    setCooked(next);
    setNotice({ id: dish.id, name: dish.name });
    void refresh(dishes, next, prefs, skip, text);
  }

  function removeCooked(id: string) {
    const next = cooked.filter((c) => c.id !== id);
    setCooked(next);
    setNotice((n) => (n?.id === id ? null : n));
    void refresh(dishes, next, prefs, skip, text);
  }

  function skipTonight(key: string) {
    const next = [...skip, key];
    setSkip(next);
    void refresh(dishes, cooked, prefs, next, text);
  }

  return {
    phase,
    text,
    setText,
    dishes,
    cooked,
    prefs,
    cousins,
    tonight,
    error,
    updating,
    notice,
    dismissed,
    dismissNotice: () => setNotice(null),
    submit,
    confirmKitchen,
    review: () => setPhase("confirm"),
    edit: () => setPhase("input"),
    setPrefs,
    markCooked,
    removeCooked,
    skipTonight,
  };
}
