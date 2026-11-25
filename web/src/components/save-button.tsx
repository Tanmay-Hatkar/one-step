"use client";

import { Heart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { toggleSaved, useSaved } from "@/lib/saved";
import type { Cousin, Dish } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Save a dish for later (it joins the shopping list); tap again to remove it. */
export function SaveButton({ dish, cousin }: { dish: Dish; cousin: Cousin | null }) {
  const { saved } = useSaved();
  const on = saved.some((s) => s.id === dish.id);
  return (
    <Button
      variant="outline"
      aria-pressed={on}
      onClick={() => toggleSaved(dish, cousin)}
      className="h-9"
    >
      <Heart aria-hidden className={cn(on && "fill-primary text-primary")} />
      {on ? "Saved" : "Save"}
    </Button>
  );
}
