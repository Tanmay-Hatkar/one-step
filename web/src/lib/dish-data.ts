import { cacheLife } from "next/cache";

import { API_URL } from "@/lib/site";
import type { DishIndexEntry, DishPage } from "@/lib/types";

/** Thrown when the API says the dish doesn't exist (→ a real 404 page). */
export class DishNotFound extends Error {}

/**
 * One catalog dish for server rendering. Cached for days: the catalog changes only on deploy.
 * Returns null if the API can't be reached, so the page can fall back to loading in the browser.
 */
export async function fetchDishPage(id: string): Promise<DishPage | null> {
  "use cache";
  cacheLife("days");
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/dishes/${encodeURIComponent(id)}`);
  } catch {
    return null;
  }
  if (response.status === 404 || response.status === 422) throw new DishNotFound(id);
  if (!response.ok) return null;
  return (await response.json()) as DishPage;
}

/** Every catalog dish, for the sitemap and the directory. Empty if the API is unreachable. */
export async function fetchDishIndex(): Promise<DishIndexEntry[]> {
  "use cache";
  cacheLife("days");
  try {
    const response = await fetch(`${API_URL}/api/dishes`);
    if (!response.ok) return [];
    return (await response.json()) as DishIndexEntry[];
  } catch {
    return [];
  }
}
