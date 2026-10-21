import type {
  Cousin,
  Diet,
  DishPage,
  DishStats,
  EvalResults,
  Have,
  KitchenMap,
  Question,
  TechniqueGuide,
  SharedKitchen,
  TonightPicks,
  UserDish,
} from "./types";

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
      // A FormData body sets its own multipart Content-Type.
      headers:
        init?.body instanceof FormData
          ? init.headers
          : { "Content-Type": "application/json", ...init?.headers },
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

/** Voice input: turn a recording into text for the repertoire box. */
export async function transcribe(clip: Blob): Promise<string> {
  const form = new FormData();
  form.append("audio", clip, "clip");
  const body = await request<{ text: string }>("/api/transcribe", { method: "POST", body: form });
  return body.text;
}

/** Dishes one step away from the user's repertoire, each written as a diff. */
export async function findCousins(
  repertoire: UserDish[],
  diet: Diet,
  have: Have,
  limit = 6,
): Promise<Cousin[]> {
  const body = await request<{ cousins: Cousin[] }>("/api/cousins", {
    method: "POST",
    body: JSON.stringify({ repertoire, diet, have, limit }),
  });
  return body.cousins;
}

/** A familiar dish, a one-step dish and a stretch that fit tonight. */
export async function getTonight(
  repertoire: UserDish[],
  diet: Diet,
  have: Have,
  maxMinutes: number | null,
  skip: string[],
): Promise<TonightPicks> {
  return request<TonightPicks>("/api/tonight", {
    method: "POST",
    body: JSON.stringify({ repertoire, diet, have, max_minutes: maxMinutes, skip }),
  });
}

/** Catalog size, for the landing line. */
export async function getStats(): Promise<DishStats> {
  return request<DishStats>("/api/dishes/stats");
}

/** Your kitchen with its closest cousins, for the map (no written diffs). */
export async function getMap(repertoire: UserDish[], diet: Diet, have: Have): Promise<KitchenMap> {
  return request<KitchenMap>("/api/map", {
    method: "POST",
    body: JSON.stringify({ repertoire, diet, have }),
  });
}

/** One dish written as a diff from your kitchen (a tap on the map). */
export async function getCousin(
  repertoire: UserDish[],
  dishId: string,
  diet: Diet,
  have: Have,
): Promise<Cousin> {
  return request<Cousin>("/api/cousin", {
    method: "POST",
    body: JSON.stringify({ repertoire, dish_id: dishId, diet, have }),
  });
}

/** A few quick questions whose answers would change the suggestions (often none). */
export async function getQuestions(
  repertoire: UserDish[],
  diet: Diet,
  have: Have,
  dismissed: string[],
): Promise<Question[]> {
  const body = await request<{ questions: Question[] }>("/api/questions", {
    method: "POST",
    body: JSON.stringify({ repertoire, diet, have, dismissed }),
  });
  return body.questions;
}

/** Save a read-only snapshot of a kitchen; returns its id. */
export async function createShare(dishes: UserDish[]): Promise<string> {
  const body = await request<{ id: string }>("/api/shares", {
    method: "POST",
    body: JSON.stringify({ dishes }),
  });
  return body.id;
}

/** Open a shared kitchen. */
export async function getShare(id: string): Promise<SharedKitchen> {
  return request<SharedKitchen>(`/api/shares/${encodeURIComponent(id)}`);
}

/** One catalog dish with its full recipe (if any). */
export async function getDishPage(id: string): Promise<DishPage> {
  return request<DishPage>(`/api/dishes/${encodeURIComponent(id)}`);
}

let recipeIds: Promise<Set<string>> | null = null;

/** Which dishes have a full recipe. Fetched once per page load and shared. */
export function getRecipeIds(): Promise<Set<string>> {
  recipeIds ??= request<string[]>("/api/recipes")
    .then((ids) => new Set(ids))
    .catch((err) => {
      recipeIds = null;
      throw err;
    });
  return recipeIds;
}

let techniques: Promise<TechniqueGuide[]> | null = null;

/** How-to cards for every technique. Fetched once per page load and shared. */
export function getTechniques(): Promise<TechniqueGuide[]> {
  techniques ??= request<TechniqueGuide[]>("/api/techniques").catch((err) => {
    techniques = null; // let a later call retry
    throw err;
  });
  return techniques;
}

/** The latest public eval results. */
export async function getEvals(): Promise<EvalResults> {
  return request<EvalResults>("/api/evals");
}
