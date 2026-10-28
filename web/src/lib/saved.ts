// Dishes you saved for later, and the shopping list they add up to. Kept inside the
// saved kitchen, so they sync with a passkey like everything else.

import { useEffect, useState } from "react";

import { emptyKitchen, loadKitchen, saveKitchen } from "./storage";
import { track } from "./track";
import type { Cousin, Dish } from "./types";

const EVENT = "one-step:saved";

export interface SavedDish {
  id: string;
  name: string;
  savedAt: string;
  /** What you'd need to buy for it (from your kitchen at the time, or the dish itself). */
  toBuy: string[];
}

export interface ShoppingItem {
  item: string;
  /** Saved dishes that need it. */
  for: string[];
}

/** What a dish needs that you don't have: the diff's new ingredients minus swaps. */
export function toBuyFor(dish: Dish, cousin: Cousin | null): string[] {
  if (!cousin) return dish.key_ingredients;
  const swapped = new Set((cousin.delta.swaps ?? []).map((s) => s.need));
  return cousin.delta.new_ingredients.filter((i) => !swapped.has(i));
}

function update(change: (k: ReturnType<typeof emptyKitchen>) => void) {
  const kitchen = loadKitchen() ?? emptyKitchen();
  change(kitchen);
  saveKitchen(kitchen);
  window.dispatchEvent(new Event(EVENT));
}

/** Add a dish to Saved, or take it off if it's there already. */
export function toggleSaved(dish: Dish, cousin: Cousin | null): void {
  update((k) => {
    if (k.saved.some((s) => s.id === dish.id)) {
      k.saved = k.saved.filter((s) => s.id !== dish.id);
    } else {
      k.saved = [
        { id: dish.id, name: dish.name, savedAt: new Date().toISOString(), toBuy: toBuyFor(dish, cousin) },
        ...k.saved,
      ];
      track("saved", dish.id);
    }
  });
}

/** Tick an item on the shopping list on or off. */
export function toggleBought(item: string): void {
  update((k) => {
    k.bought = k.bought.includes(item) ? k.bought.filter((i) => i !== item) : [...k.bought, item];
  });
}

export function clearBought(): void {
  update((k) => {
    k.bought = [];
  });
}

/** Every item the saved dishes need, once each, with the dishes that need it. */
export function shoppingList(saved: SavedDish[]): ShoppingItem[] {
  const items = new Map<string, string[]>();
  for (const dish of saved) {
    for (const raw of dish.toBuy) {
      const item = raw.toLowerCase();
      items.set(item, [...(items.get(item) ?? []), dish.name]);
    }
  }
  return [...items.entries()].map(([item, dishes]) => ({ item, for: dishes }));
}

/** Saved dishes and bought items, kept in step across the page. */
export function useSaved() {
  const [state, setState] = useState<{ saved: SavedDish[]; bought: string[] }>({
    saved: [],
    bought: [],
  });
  useEffect(() => {
    const read = () => {
      const k = loadKitchen();
      setState({ saved: k?.saved ?? [], bought: k?.bought ?? [] });
    };
    read();
    window.addEventListener(EVENT, read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener(EVENT, read);
      window.removeEventListener("storage", read);
    };
  }, []);
  return state;
}
