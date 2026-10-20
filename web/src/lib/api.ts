import type { Cousin, Diet, DishStats, TonightPicks, UserDish } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** An error whose message is safe to show the user as-is. */
export class ApiError extends Error {}

const FRIENDLY: Record<number, string> = {
  429: "You're going fast! Give it a minute and try again.",
  502: "Couldn't reach the kitchen brain just now. Please try again.",
  503: "One Step is resting for today. Try again tomorrow.",
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Can't reach One Step right now. Check your connection.");
  }
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json())?.detail;
    } catch {
      detail = undefined;
    }
    const message =
      typeof detail === "string" ? detail : FRIENDLY[response.status] ?? "Something went wrong.";
    throw new ApiError(message);
  }
  return (await response.json()) as T;
}

/** Turn "what I usually cook" text into the user's dishes. */
export async function parseRepertoire(text: string): Promise<UserDish[]> {
  const body = await request<{ dishes: UserDish[] }>("/api/repertoire/parse", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  return body.dishes;
}

/** Dishes one step away from the user's repertoire, each written as a diff. */
export async function findCousins(
  repertoire: UserDish[],
  diet: Diet,
  limit = 6,
): Promise<Cousin[]> {
  const body = await request<{ cousins: Cousin[] }>("/api/cousins", {
    method: "POST",
    body: JSON.stringify({ repertoire, diet, limit }),
  });
  return body.cousins;
}

/** A familiar dish, a one-step dish and a stretch that fit tonight. */
export async function getTonight(
  repertoire: UserDish[],
  diet: Diet,
  maxMinutes: number | null,
  skip: string[],
): Promise<TonightPicks> {
  return request<TonightPicks>("/api/tonight", {
    method: "POST",
    body: JSON.stringify({ repertoire, diet, max_minutes: maxMinutes, skip }),
  });
}

/** Catalog size, for the landing line. */
export async function getStats(): Promise<DishStats> {
  return request<DishStats>("/api/dishes/stats");
}
