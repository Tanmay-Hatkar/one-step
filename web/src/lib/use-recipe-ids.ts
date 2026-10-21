"use client";

import { useEffect, useState } from "react";

import { getRecipeIds } from "./api";

/** Dish ids that have a full recipe; empty until loaded (or if it fails). */
export function useRecipeIds(): Set<string> {
  const [ids, setIds] = useState<Set<string>>(() => new Set());
  useEffect(() => {
    let live = true;
    getRecipeIds()
      .then((found) => live && setIds(found))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  return ids;
}
