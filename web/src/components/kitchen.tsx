"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { CousinCard } from "@/components/cousin-card";
import { LoadingCards } from "@/components/loading-cards";
import { RepertoireSummary } from "@/components/repertoire-summary";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, findCousins, getStats, parseRepertoire } from "@/lib/api";
import { loadKitchen, saveKitchen } from "@/lib/storage";
import type { Cousin, DishStats, UserDish } from "@/lib/types";

const EXAMPLE =
  "Most nights I make a whole chicken leg marinated in Indian spices, with rice made in " +
  "the rice cooker with garlic, onion and a chicken broth cube. Some weekends I make a " +
  "full chicken biryani.";

const MAX_CHARS = 1500;

type Phase = "input" | "reading" | "finding" | "results";

export function Kitchen() {
  const [phase, setPhase] = useState<Phase>("input");
  const [text, setText] = useState("");
  const [dishes, setDishes] = useState<UserDish[]>([]);
  const [cousins, setCousins] = useState<Cousin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DishStats | null>(null);

  useEffect(() => {
    // Restoring from localStorage must happen after hydration, in an effect.
    const saved = loadKitchen();
    if (saved?.cousins.length) {
      /* eslint-disable react-hooks/set-state-in-effect */
      setText(saved.text);
      setDishes(saved.dishes);
      setCousins(saved.cousins);
      setPhase("results");
      /* eslint-enable react-hooks/set-state-in-effect */
    }
    getStats().then(setStats).catch(() => setStats(null));
  }, []);

  async function run() {
    const input = text.trim();
    if (input.length < 3) {
      setError("Tell me about a dish or two you cook.");
      return;
    }
    setError(null);
    try {
      setPhase("reading");
      const parsed = await parseRepertoire(input);
      setDishes(parsed);
      setPhase("finding");
      const found = await findCousins(parsed);
      setCousins(found);
      setPhase("results");
      saveKitchen({ text: input, dishes: parsed, cousins: found });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setPhase("input");
    }
  }

  const busy = phase === "reading" || phase === "finding";

  return (
    <div className="space-y-8">
      {(phase === "input" || busy) && (
        <section aria-labelledby="ask" className="space-y-3">
          <label id="ask" htmlFor="repertoire" className="block text-base font-medium">
            What do you usually cook?
          </label>
          <Textarea
            id="repertoire"
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
            placeholder="Describe a dish or two the way you'd tell a friend — what goes in, how you cook it."
            className="min-h-32 bg-card text-base"
            disabled={busy}
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Button
              variant="link"
              className="h-auto px-0 text-muted-foreground"
              onClick={() => setText(EXAMPLE)}
              disabled={busy}
            >
              <Sparkles aria-hidden />
              Try an example
            </Button>
            <Button size="lg" onClick={run} disabled={busy} className="px-4">
              Show me what&apos;s one step away
              <ArrowRight aria-hidden />
            </Button>
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {stats && !busy && (
            <p className="text-xs text-muted-foreground">
              {stats.dishes} home dishes from {stats.regions} regions, connected by how
              they&apos;re cooked.
            </p>
          )}
        </section>
      )}

      {phase === "reading" && <LoadingCards label="Reading your kitchen…" />}
      {phase === "finding" && (
        <>
          <RepertoireSummary dishes={dishes} onEdit={() => setPhase("input")} />
          <LoadingCards label="Finding dishes one step away…" />
        </>
      )}

      {phase === "results" && (
        <>
          <RepertoireSummary dishes={dishes} onEdit={() => setPhase("input")} />
          <section aria-labelledby="cousins" className="space-y-4">
            <h2 id="cousins" className="font-heading text-xl font-semibold">
              {cousins.length
                ? "You're one step away from…"
                : "Nothing close enough yet — try describing another dish."}
            </h2>
            {cousins.map((cousin, i) => (
              <CousinCard key={cousin.dish.id} cousin={cousin} index={i} />
            ))}
          </section>
        </>
      )}
    </div>
  );
}
