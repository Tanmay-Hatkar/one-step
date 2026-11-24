// Recipes you pasted from somewhere else, each written as a step from your kitchen. Kept
// inside the saved kitchen (this device, plus your passkey sync), never on our servers.

import { useEffect, useState } from "react";

import { emptyKitchen, loadKitchen, saveKitchen, type PastedEntry } from "./storage";
import { track } from "./track";
import type { Pasted, Recipe } from "./types";

const EVENT = "one-step:pasted";
const SHARED_KEY = "one-step:shared";

/** Oldest pastes drop off after this many, so the synced kitchen stays small. */
export const MAX_PASTED = 12;
/** Longest text sent to the API. Mirrors max_paste_chars in api/app/config.py. */
export const MAX_PASTE_CHARS = 8000;

/** Pasted dishes aren't in the catalog; their ids say so. */
export function isPasted(id: string): boolean {
  return id.startsWith("pasted_");
}

function update(change: (pasted: PastedEntry[]) => PastedEntry[]) {
  const kitchen = loadKitchen() ?? emptyKitchen();
  kitchen.pasted = change(kitchen.pasted);
  saveKitchen(kitchen);
  window.dispatchEvent(new Event(EVENT));
}

/** Keep a pasted recipe (pasting the same one again replaces it). */
export function addPasted(pasted: Pasted, fromPhoto = false): void {
  const id = pasted.cousin.dish.id;
  update((all) =>
    [
      { ...pasted, pastedAt: new Date().toISOString(), fromPhoto },
      ...all.filter((p) => p.cousin.dish.id !== id),
    ].slice(0, MAX_PASTED),
  );
  track("pasted");
}

export function removePasted(id: string): void {
  update((all) => all.filter((p) => p.cousin.dish.id !== id));
}

/** A pasted recipe on this device, by dish id. */
export function findPasted(id: string): PastedEntry | null {
  return loadKitchen()?.pasted.find((p) => p.cousin.dish.id === id) ?? null;
}

/** The pasted recipe in the shape cook mode and the dish page use. */
export function pastedAsRecipe(entry: PastedEntry): Recipe | null {
  if (!entry.recipe.steps.length) return null;
  return {
    title: entry.cousin.dish.name,
    source_url: entry.recipe.source_url ?? "",
    revision: 0,
    ingredients: entry.recipe.ingredients,
    steps: entry.recipe.steps,
    source_name: "",
    authors: "",
    license: "",
    license_url: "",
  };
}

/** Pasted recipes, kept in step across the page. */
export function usePasted(): PastedEntry[] {
  const [pasted, setPasted] = useState<PastedEntry[]>([]);
  useEffect(() => {
    const read = () => setPasted(loadKitchen()?.pasted ?? []);
    read();
    window.addEventListener(EVENT, read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener(EVENT, read);
      window.removeEventListener("storage", read);
    };
  }, []);
  return pasted;
}

/**
 * When another app shares a link or text to One Step (the installed app is a share
 * target), it arrives as ?url= / ?text= / ?title=. Hold it for the paste box, which may
 * only appear after the kitchen is set up, and tidy the address bar.
 *
 * Returns true if something was shared.
 */
export function captureShared(): boolean {
  try {
    const params = new URLSearchParams(window.location.search);
    const url = params.get("url")?.trim();
    const text = params.get("text")?.trim();
    const shared = url || text;
    if (!shared) return window.sessionStorage.getItem(SHARED_KEY) !== null;
    // Some apps put the link in `text` and a caption in `title`; keep whatever came.
    const title = params.get("title")?.trim();
    const all = url && text && !text.includes(url) ? `${text}\n${url}` : shared;
    window.sessionStorage.setItem(
      SHARED_KEY,
      (title && !all.includes(title) ? `${title}\n${all}` : all).slice(0, MAX_PASTE_CHARS),
    );
    window.history.replaceState(null, "", window.location.pathname);
    return true;
  } catch {
    return false;
  }
}

/** Take what was shared (once). */
export function takeShared(): string | null {
  try {
    const shared = window.sessionStorage.getItem(SHARED_KEY);
    window.sessionStorage.removeItem(SHARED_KEY);
    return shared;
  } catch {
    return null;
  }
}
