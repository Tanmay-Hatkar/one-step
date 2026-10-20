import { ArrowRight, ChevronDown, Plus, Sparkles } from "lucide-react";

import { DietPicker, dietSummary } from "@/components/diet-picker";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { VoiceInput } from "@/components/voice-input";
import type { Diet } from "@/lib/types";

const EXAMPLE =
  "Most nights I make a whole chicken leg marinated in Indian spices, with rice made in " +
  "the rice cooker with garlic, onion and a chicken broth cube. Some weekends I make a " +
  "full chicken biryani.";

/** Tap to add a common dish, so nobody has to start from a blank box. */
const STARTERS: { label: string; text: string }[] = [
  { label: "Dal and rice", text: "Dal with rice — toor dal with turmeric, tempered with cumin and garlic." },
  { label: "Pasta", text: "Pasta in a garlicky tomato sauce with chili flakes." },
  { label: "Stir-fry", text: "Chicken and vegetable stir-fry with soy sauce, garlic and ginger, over rice." },
  { label: "Eggs", text: "Scrambled eggs with onion, tomato and green chili, on toast." },
  { label: "Curry", text: "Chicken curry with onion, tomato, ginger-garlic paste and garam masala." },
  { label: "Tacos", text: "Ground beef tacos with cumin, onion and salsa in flour tortillas." },
];

export const MAX_CHARS = 1500;

export function StartForm({
  text,
  onText,
  diet,
  onDiet,
  onSubmit,
  busy,
  error,
}: {
  text: string;
  onText: (text: string) => void;
  diet: Diet;
  onDiet: (diet: Diet) => void;
  onSubmit: () => void;
  busy: boolean;
  error: string | null;
}) {
  function addStarter(starter: string) {
    const joined = text.trim() ? `${text.trim()} ${starter}` : starter;
    onText(joined.slice(0, MAX_CHARS));
  }
  // Talking again adds to what's there, like tapping another starter.
  const addSpoken = addStarter;

  return (
    <section aria-labelledby="ask" className="space-y-4">
      <label id="ask" htmlFor="repertoire" className="block text-base font-medium">
        What do you usually cook?
      </label>
      <Textarea
        id="repertoire"
        value={text}
        onChange={(e) => onText(e.target.value.slice(0, MAX_CHARS))}
        placeholder="Describe a dish or two the way you'd tell a friend — what goes in, how you cook it. Or tap the mic and just say it."
        className="min-h-32 bg-card text-base"
        disabled={busy}
      />
      <VoiceInput onText={addSpoken} disabled={busy} />
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">Or tap to add one:</p>
        <div className="flex flex-wrap gap-2">
          {STARTERS.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => addStarter(s.text)}
              disabled={busy}
              className="inline-flex h-8 items-center gap-1 rounded-full border bg-card px-3 text-sm hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none disabled:opacity-50"
            >
              <Plus aria-hidden className="size-3.5 text-muted-foreground" />
              {s.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onText(EXAMPLE)}
            disabled={busy}
            className="inline-flex h-8 items-center gap-1 rounded-full px-2 text-sm text-muted-foreground underline-offset-4 hover:underline disabled:opacity-50"
          >
            <Sparkles aria-hidden className="size-3.5" />
            Try an example
          </button>
        </div>
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

      <Button size="lg" onClick={onSubmit} disabled={busy} className="h-11 w-full text-base sm:w-auto sm:px-5">
        Show me what&apos;s one step away
        <ArrowRight aria-hidden />
      </Button>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </section>
  );
}
