"use client";

import { ArrowRight, ChevronDown, Keyboard } from "lucide-react";
import { useState } from "react";

import { DietPicker, dietSummary } from "@/components/diet-picker";
import { DishPicker } from "@/components/dish-picker";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { VoiceInput } from "@/components/voice-input";
import { STARTER_DISHES } from "@/lib/starters";
import type { Diet } from "@/lib/types";

export const MAX_CHARS = 1500;

/**
 * Start by tapping dishes you make (no typing, no AI wait). Anything not on the tiles
 * can be said out loud or typed, and the AI reads it.
 */
export function StartForm({
  text,
  onText,
  picked,
  onToggle,
  diet,
  onDiet,
  onSubmit,
  busy,
  error,
}: {
  text: string;
  onText: (text: string) => void;
  picked: string[];
  onToggle: (id: string) => void;
  diet: Diet;
  onDiet: (diet: Diet) => void;
  onSubmit: () => void;
  busy: boolean;
  error: string | null;
}) {
  const [typing, setTyping] = useState(false);
  const showText = typing || text.trim().length > 0;
  const said = text.trim().length > 0;
  const count = picked.length + (said ? 1 : 0);

  // Talking again adds to what's there.
  function addSpoken(spoken: string) {
    const joined = text.trim() ? `${text.trim()} ${spoken}` : spoken;
    onText(joined.slice(0, MAX_CHARS));
  }

  return (
    <section aria-labelledby="ask" className="space-y-5">
      <div className="space-y-1">
        <h2 id="ask" className="text-lg font-semibold">
          What do you cook often?
        </h2>
        <p className="text-sm text-muted-foreground">Tap the ones you make. Pick two or three.</p>
      </div>

      <DishPicker dishes={STARTER_DISHES} picked={picked} onToggle={onToggle} disabled={busy} />

      <div className="space-y-3 rounded-xl border bg-card p-4">
        <p className="text-sm">
          <span className="font-medium">Not here, or you make it your own way?</span>{" "}
          <span className="text-muted-foreground">Tell me how you make it.</span>
        </p>
        <VoiceInput onText={addSpoken} disabled={busy} />
        {showText ? (
          <Textarea
            id="repertoire"
            aria-label="How you make it"
            value={text}
            onChange={(e) => onText(e.target.value.slice(0, MAX_CHARS))}
            placeholder="e.g. Rice in the rice cooker with garlic, onion and a stock cube, and a chicken leg marinated in Indian spices."
            className="min-h-28 bg-background text-base"
            disabled={busy}
            autoFocus={typing && !said}
          />
        ) : (
          <button
            type="button"
            onClick={() => setTyping(true)}
            disabled={busy}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            <Keyboard aria-hidden className="size-4" />
            Type it instead
          </button>
        )}
      </div>

      <details className="group rounded-xl border bg-card px-4 py-3">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm">
          <span>
            <span className="font-medium">Diet &amp; allergies</span>
            <span className="text-muted-foreground"> · {dietSummary(diet)}</span>
          </span>
          <ChevronDown
            aria-hidden
            className="size-4 text-muted-foreground transition-transform group-open:rotate-180"
          />
        </summary>
        <div className="pt-3">
          <DietPicker diet={diet} onChange={onDiet} />
        </div>
      </details>

      <div className="sticky bottom-4 z-10 space-y-2">
        <Button
          size="lg"
          onClick={onSubmit}
          disabled={busy}
          className="h-12 w-full text-base shadow-lg sm:w-auto sm:px-6"
        >
          {count ? `Show me new dishes (${count})` : "Show me new dishes"}
          <ArrowRight aria-hidden />
        </Button>
        {error && (
          <p role="alert" className="rounded-lg bg-background/95 px-1 text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}
