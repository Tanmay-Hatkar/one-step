"use client";

import { Check, ChevronDown, Plus, X } from "lucide-react";
import { type FormEvent, useState } from "react";

import { ToggleChip } from "@/components/toggle-chip";
import { Button } from "@/components/ui/button";
import { EQUIPMENT } from "@/lib/labels";
import type { Have } from "@/lib/types";

const MAX_PANTRY = 60;
const MAX_NAME = 40;

/** "Oven, wok · 3 in the pantry" — or a nudge when nothing is set. */
export function haveSummary(have: Have): string {
  const parts: string[] = [];
  const named = have.equipment
    .map((id) => EQUIPMENT.find((e) => e.id === id)?.label.toLowerCase() ?? id)
    .slice(0, 2);
  if (named.length) {
    const more = have.equipment.length - named.length;
    parts.push(named.join(", ") + (more > 0 ? ` +${more}` : ""));
  }
  if (have.ingredients.length) parts.push(`${have.ingredients.length} in the pantry`);
  return parts.length ? parts.join(" · ") : "Add tools and pantry items";
}

/**
 * What the user has beyond what their dishes imply. Equipment unlocks dishes (no new
 * equipment is one step); pantry items shrink "You may need" and enable swaps.
 */
export function WhatIHave({
  have,
  implied,
  suggested,
  onChange,
}: {
  have: Have;
  /** Equipment their dishes already use — shown as on, can't be turned off here. */
  implied: string[];
  /** Ingredients their suggestions often need, offered as one-tap adds. */
  suggested: string[];
  onChange: (have: Have) => void;
}) {
  const [draft, setDraft] = useState("");
  const pantry = new Set(have.ingredients.map((i) => i.toLowerCase()));

  function toggleEquipment(id: string) {
    const equipment = have.equipment.includes(id)
      ? have.equipment.filter((e) => e !== id)
      : [...have.equipment, id];
    onChange({ ...have, equipment });
  }

  function addIngredient(name: string) {
    const clean = name.trim().toLowerCase().slice(0, MAX_NAME);
    if (!clean || pantry.has(clean) || have.ingredients.length >= MAX_PANTRY) return;
    onChange({ ...have, ingredients: [...have.ingredients, clean] });
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    // "lemon, soy sauce" adds both.
    const names = draft.split(",").map((n) => n.trim()).filter(Boolean);
    const next = [...have.ingredients];
    for (const n of names) {
      const clean = n.toLowerCase().slice(0, MAX_NAME);
      if (!next.includes(clean) && next.length < MAX_PANTRY) next.push(clean);
    }
    onChange({ ...have, ingredients: next });
    setDraft("");
  }

  const quickAdds = suggested.filter((s) => !pantry.has(s.toLowerCase())).slice(0, 6);

  return (
    <details className="group rounded-xl border bg-card px-4 py-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm">
        <span>
          <span className="font-medium">What I have</span>
          <span className="text-muted-foreground"> · {haveSummary(have)}</span>
        </span>
        <ChevronDown
          aria-hidden
          className="size-4 text-muted-foreground transition-transform group-open:rotate-180"
        />
      </summary>

      <div className="space-y-4 pt-3">
        <div>
          <p className="mb-2 text-xs text-muted-foreground">
            Tools — new tools unlock new dishes
          </p>
          <div className="flex flex-wrap gap-2">
            {EQUIPMENT.map(({ id, label }) => {
              const fromDishes = implied.includes(id) || id === "stovetop";
              const on = fromDishes || have.equipment.includes(id);
              return fromDishes ? (
                <span
                  key={id}
                  className="inline-flex h-8 items-center gap-1 rounded-full border border-primary/30 px-3 text-sm text-muted-foreground"
                  title="From your dishes"
                >
                  <Check aria-hidden className="size-3.5 text-primary" />
                  {label}
                </span>
              ) : (
                <ToggleChip key={id} pressed={on} onClick={() => toggleEquipment(id)}>
                  {on && <Check aria-hidden className="size-3.5" />}
                  {label}
                </ToggleChip>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Pantry — I&apos;ll suggest swaps from what you have
          </p>
          {have.ingredients.length > 0 && (
            <ul className="flex flex-wrap gap-1.5" aria-label="Pantry">
              {have.ingredients.map((item) => (
                <li
                  key={item}
                  className="inline-flex h-7 items-center gap-0.5 rounded-full border bg-background pr-1 pl-2.5 text-sm"
                >
                  {item}
                  <button
                    type="button"
                    onClick={() =>
                      onChange({ ...have, ingredients: have.ingredients.filter((i) => i !== item) })
                    }
                    aria-label={`Remove ${item}`}
                    className="grid size-5 place-items-center rounded-full text-muted-foreground hover:bg-muted"
                  >
                    <X aria-hidden className="size-3" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form onSubmit={submit} className="flex gap-2">
            <label htmlFor="pantry-add" className="sr-only">
              Add pantry items
            </label>
            <input
              id="pantry-add"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="e.g. lemon, soy sauce"
              maxLength={200}
              className="h-9 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            />
            <Button type="submit" variant="outline" className="h-9" disabled={!draft.trim()}>
              Add
            </Button>
          </form>
          {quickAdds.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs text-muted-foreground">Your suggestions often need — got any?</p>
              <div className="flex flex-wrap gap-1.5">
                {quickAdds.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => addIngredient(item)}
                    className="inline-flex h-7 items-center gap-1 rounded-full border border-dashed px-2.5 text-sm hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                  >
                    <Plus aria-hidden className="size-3 text-muted-foreground" />
                    {item}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </details>
  );
}
