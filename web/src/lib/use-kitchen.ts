"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, findCousins, getTonight, parseRepertoire } from "./api";
import { MAX_LOG, recentNames } from "./cooklog";
import { cookedToUserDish, repertoireOf } from "./kitchen";
import { pickedToUserDish, startersById } from "./starters";
import { track } from "./track";
import {
  type CookLogEntry,
  type CookedDish,
  DEFAULT_PREFS,
  type Prefs,
  emptyKitchen,
  loadKitchen,
  saveKitchen,
} from "./storage";
import type { Cousin, Dish, Have, TonightPicks, UserDish } from "./types";

export type Phase = "input" | "reading" | "confirm" | "finding" | "results";

/** Wait this long after the last preference change before asking the API again. */
const PREFS_DEBOUNCE_MS = 400;

/** A short message after cooking something, with a way to undo it. */
export interface CookedNotice {
  /** Catalog (or pasted) id of a new dish that joined the kitchen; null for one of your own. */
  id: string | null;
  name: string;
  /** How many more dishes became one step away because of it. */
  unlocked: number;
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
  const [picked, setPickedState] = useState<string[]>([]);
  const [log, setLogState] = useState<CookLogEntry[]>([]);
  const [reach, setReach] = useState<number | null>(null);

  // Only the latest request may update the page (preferences can change mid-flight).
  const requestId = useRef(0);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Answered questions and picked tiles are remembered alongside everything else.
  const dismissedRef = useRef<string[]>([]);
  const pickedRef = useRef<string[]>([]);
  const logRef = useRef<CookLogEntry[]>([]);
  const persist = useCallback(
    (next: { text: string; dishes: UserDish[]; cooked: CookedDish[]; prefs: Prefs; cousins: Cousin[] }) =>
      // Keep what other pages store in the kitchen too (saved dishes, shopping list).
      saveKitchen({
        ...(loadKitchen() ?? emptyKitchen()),
        ...next,
        dismissed: dismissedRef.current,
        picked: pickedRef.current,
        log: logRef.current,
      }),
    [],
  );

  /** Fetch cousins and tonight's picks; returns them with the reach, or null if stale. */
  const fetchAll = useCallback(
    async (own: UserDish[], done: CookedDish[], p: Prefs, skipped: string[]) => {
      const id = ++requestId.current;
      const repertoire = repertoireOf(own, done);
      const [found, picks] = await Promise.all([
        findCousins(repertoire, p.diet, p.have),
        getTonight(repertoire, p.diet, p.have, p.minutes, skipped, recentNames(logRef.current)),
      ]);
      if (id !== requestId.current) return null;
      setCousins(found);
      setTonight(picks);
      setReach(picks.reach ?? null);
      return { found, reach: picks.reach ?? null };
    },
    [],
  );

  /** Re-fetch after a change on the results page, keeping the current results visible. */
  const refresh = useCallback(
    async (own: UserDish[], done: CookedDish[], p: Prefs, skipped: string[], t: string) => {
      setUpdating(true);
      setError(null);
      try {
        const result = await fetchAll(own, done, p, skipped);
        if (result) {
          persist({ text: t, dishes: own, cooked: done, prefs: p, cousins: result.found });
        }
        return result;
      } catch (err) {
        setError(messageOf(err));
        return null;
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
    setPickedState(saved.picked);
    pickedRef.current = saved.picked;
    setLogState(saved.log);
    logRef.current = saved.log;
    if (saved.dishes.length && !saved.cousins.length) {
      setPhase("confirm"); // they left while checking what was heard
    } else if (saved.dishes.length) {
      setCousins(saved.cousins);
      setPhase("results");
      void refresh(saved.dishes, saved.cooked, saved.prefs, [], saved.text);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [refresh]);

  const dismissNotice = useCallback(() => setNotice(null), []);

  function togglePicked(id: string) {
    const next = picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id];
    pickedRef.current = next;
    setPickedState(next);
    setError(null);
  }

  /**
   * Tapped tiles are catalog dishes, so they go straight to results. Anything typed or
   * said is read by the AI first and shown back ("Here's what I heard") to fix guesses.
   */
  async function submit() {
    const input = text.trim();
    const tiles = startersById(picked).map(pickedToUserDish);
    if (input.length < 3 && !tiles.length) {
      setError("Tap a dish you make, or tell me about one.");
      return;
    }
    setError(null);
    setSkip([]);
    if (input.length < 3) {
      setText("");
      await confirmKitchen(tiles, prefs.have, [], "");
      return;
    }
    try {
      setPhase("reading");
      const parsed = await parseRepertoire(input);
      const said = new Set(parsed.map((d) => d.matched_dish_id).filter(Boolean));
      const all = [...parsed, ...tiles.filter((t) => !said.has(t.matched_dish_id))];
      setDishes(all);
      setCousins([]);
      setTonight(null);
      // Show what was understood before searching, so guesses can be fixed first.
      setPhase("confirm");
      persist({ text: input, dishes: all, cooked, prefs, cousins: [] });
    } catch (err) {
      setError(messageOf(err));
      setPhase("input");
    }
  }

  /** Accept the checked kitchen (and any answers), then find dishes. */
  async function confirmKitchen(
    checked: UserDish[],
    have: Have,
    answered: string[],
    t: string = text,
  ) {
    const nextPrefs = { ...prefs, have };
    const nextDismissed = [...new Set([...dismissed, ...answered])];
    dismissedRef.current = nextDismissed;
    setDismissed(nextDismissed);
    setDishes(checked);
    setPrefsState(nextPrefs);
    setError(null);
    setSkip([]);
    setPhase("finding");
    // Save the checked kitchen first, so nothing is lost if the search fails or is slow.
    persist({ text: t, dishes: checked, cooked, prefs: nextPrefs, cousins: [] });
    try {
      const result = await fetchAll(checked, cooked, nextPrefs, []);
      setPhase("results");
      track("kitchen_built");
      if (result) {
        persist({ text: t, dishes: checked, cooked, prefs: nextPrefs, cousins: result.found });
      }
    } catch (err) {
      setError(messageOf(err));
      setPhase(t ? "confirm" : "input");
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

  function setLog(next: CookLogEntry[]) {
    logRef.current = next.slice(0, MAX_LOG);
    setLogState(logRef.current);
  }

  /** A new dish was cooked: it joins the kitchen, and the kitchen's reach grows. */
  async function markCooked(dish: Dish) {
    if (cooked.some((c) => c.id === dish.id)) return;
    const at = new Date().toISOString();
    const next = [...cooked, { id: dish.id, name: dish.name, cookedAt: at, dish: cookedToUserDish(dish) }];
    // The dish itself stops being "one step away" once cooked, so don't count its exit.
    const shown = [tonight?.one_step, tonight?.stretch, ...cousins].find((c) => c?.dish.id === dish.id);
    const before = reach === null ? null : reach - (shown?.delta.is_one_step ? 1 : 0);
    setCooked(next);
    setLog([{ name: dish.name, at }, ...logRef.current]);
    setNotice({ id: dish.id, name: dish.name, unlocked: 0 });
    track("cooked", dish.id);
    const result = await refresh(dishes, next, prefs, skip, text);
    const gained = result?.reach != null && before != null ? result.reach - before : 0;
    if (gained > 0) {
      setNotice((n) => (n?.id === dish.id ? { ...n, unlocked: gained } : n));
    }
  }

  function removeCooked(id: string) {
    const gone = cooked.find((c) => c.id === id);
    const next = cooked.filter((c) => c.id !== id);
    setCooked(next);
    if (gone) setLog(logRef.current.filter((e) => !(e.name === gone.name && e.at === gone.cookedAt)));
    setNotice((n) => (n?.id === id ? null : n));
    void refresh(dishes, next, prefs, skip, text);
  }

  /** One of your own dishes was cooked tonight: remember when, so it rests for a while. */
  function madeIt(name: string) {
    setLog([{ name, at: new Date().toISOString() }, ...logRef.current]);
    setNotice({ id: null, name, unlocked: 0 });
    track("cooked");
    persist({ text, dishes, cooked, prefs, cousins });
  }

  /** Take back the latest "I made this" for one of your own dishes. */
  function undoMadeIt(name: string) {
    const i = logRef.current.findIndex((e) => e.name === name);
    if (i >= 0) setLog(logRef.current.filter((_, j) => j !== i));
    setNotice(null);
    persist({ text, dishes, cooked, prefs, cousins });
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
    log,
    reach,
    madeIt,
    undoMadeIt,
    dismissed,
    picked,
    togglePicked,
    dismissNotice,
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
