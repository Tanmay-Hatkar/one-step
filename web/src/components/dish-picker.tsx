"use client";

import { Check } from "lucide-react";

import { DishPhoto } from "@/components/dish-photo";
import type { Dish } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Photo tiles of common home dishes: tap the ones you make (no typing needed). */
export function DishPicker({
  dishes,
  picked,
  onToggle,
  disabled,
}: {
  dishes: Dish[];
  picked: string[];
  onToggle: (id: string) => void;
  disabled?: boolean;
}) {
  return (
    <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
      {dishes.map((dish) => {
        const on = picked.includes(dish.id);
        return (
          <li key={dish.id}>
            <button
              type="button"
              aria-pressed={on}
              onClick={() => onToggle(dish.id)}
              disabled={disabled}
              className={cn(
                "group relative flex h-full w-full flex-col justify-start overflow-hidden rounded-xl border-2 bg-card text-left transition-colors",
                "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none disabled:opacity-50",
                on ? "border-primary" : "border-transparent hover:border-border",
              )}
            >
              <DishPhoto id={dish.id} name="" size={160} className="aspect-square w-full" />
              <span
                aria-hidden
                className={cn(
                  "absolute top-1.5 right-1.5 flex size-6 items-center justify-center rounded-full border-2 transition-colors",
                  on
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-white/90 bg-black/20",
                )}
              >
                {on && <Check className="size-3.5" strokeWidth={3} />}
              </span>
              <span className="line-clamp-2 block px-2 py-1.5 text-[13px] leading-snug font-medium sm:text-sm">
                {dish.name}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
