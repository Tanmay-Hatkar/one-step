"use client";

import { ChevronDown, CookingPot, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { AccountCard } from "@/components/account-card";
import { ConfirmKitchen } from "@/components/confirm-kitchen";
import { CousinCard } from "@/components/cousin-card";
import { DietPicker, dietSummary } from "@/components/diet-picker";
import { Hero } from "@/components/hero";
import { KitchenMap } from "@/components/kitchen-map";
import { LoadingCards } from "@/components/loading-cards";
import { RepertoireSummary } from "@/components/repertoire-summary";
import { StartForm } from "@/components/start-form";
import { Tonight } from "@/components/tonight";
import { WhatIHave } from "@/components/what-i-have";
import { Button } from "@/components/ui/button";
import { getStats } from "@/lib/api";
import { impliedEquipment, oftenNeeded, repertoireOf } from "@/lib/kitchen";
import type { DishStats } from "@/lib/types";
import { useKitchen } from "@/lib/use-kitchen";
import { cn } from "@/lib/utils";

export function Kitchen() {
  const k = useKitchen();
  const [stats, setStats] = useState<DishStats | null>(null);
  const [view, setView] = useState<"suggestions" | "map">("suggestions");

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  const busy = k.phase === "reading" || k.phase === "finding";
  const isCooked = (id: string) => k.cooked.some((c) => c.id === id);
  const tonightIds = new Set(
    [k.tonight?.one_step?.dish.id, k.tonight?.stretch?.dish.id].filter(Boolean),
  );
  const more = k.cousins.filter((c) => !tonightIds.has(c.dish.id));

  if (k.phase === "confirm") {
    return (
      <ConfirmKitchen
        dishes={k.dishes}
        cooked={k.cooked}
        diet={k.prefs.diet}
        have={k.prefs.have}
        dismissed={k.dismissed}
        error={k.error}
        onConfirm={k.confirmKitchen}
        onBack={k.edit}
      />
    );
  }

  if (k.phase !== "results") {
    return (
      <>
        <Hero />
        <div className="space-y-8">
          <StartForm
            text={k.text}
            onText={k.setText}
            diet={k.prefs.diet}
            onDiet={(diet) => k.setPrefs({ ...k.prefs, diet })}
            onSubmit={k.submit}
            busy={busy}
            error={k.error}
          />
          {stats && !busy && (
            <p className="text-xs text-muted-foreground">
              {stats.dishes} home dishes from {stats.regions} regions, connected
              by how they&apos;re cooked.
            </p>
          )}
          {!busy && <AccountCard variant="start" />}
          {k.phase === "reading" && (
            <LoadingCards label="Reading your kitchen…" />
          )}
          {k.phase === "finding" && (
            <LoadingCards label="Finding dishes one step away…" />
          )}
        </div>
      </>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium tracking-wide text-primary">
          One Step
        </p>
        <p
          role="status"
          aria-live="polite"
          className={cn(
            "flex items-center gap-1.5 text-xs text-muted-foreground transition-opacity",
            k.updating ? "opacity-100" : "opacity-0",
          )}
        >
          <Loader2 aria-hidden className="size-3.5 animate-spin" />
          {k.updating ? "Updating…" : ""}
        </p>
      </header>

      {k.notice && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl bg-accent px-4 py-3 text-sm text-accent-foreground animate-in fade-in"
        >
          <CookingPot aria-hidden className="mt-0.5 size-4 shrink-0" />
          <p className="flex-1">
            <span className="font-medium">{k.notice.name}</span> is in your
            kitchen now. New dishes grow from it.
          </p>
          <button
            type="button"
            onClick={() => k.removeCooked(k.notice!.id)}
            className="font-medium underline underline-offset-2"
          >
            Undo
          </button>
          <button type="button" onClick={k.dismissNotice} aria-label="Dismiss">
            <X aria-hidden className="size-4" />
          </button>
        </div>
      )}

      <div className="space-y-4">
        <RepertoireSummary
          dishes={k.dishes}
          cooked={k.cooked}
          onEdit={k.edit}
          onReview={k.review}
          onRemoveCooked={k.removeCooked}
          shareable={repertoireOf(k.dishes, k.cooked)}
        />
        <details className="group rounded-xl border bg-card px-4 py-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm">
            <span>
              <span className="font-medium">Diet &amp; allergies</span>
              <span className="text-muted-foreground">
                {" "}
                · {dietSummary(k.prefs.diet)}
              </span>
            </span>
            <ChevronDown
              aria-hidden
              className="size-4 text-muted-foreground transition-transform group-open:rotate-180"
            />
          </summary>
          <div className="pt-3">
            <DietPicker
              diet={k.prefs.diet}
              onChange={(diet) => k.setPrefs({ ...k.prefs, diet })}
            />
          </div>
        </details>
        <WhatIHave
          have={k.prefs.have}
          implied={impliedEquipment(repertoireOf(k.dishes, k.cooked))}
          suggested={oftenNeeded(
            [k.tonight?.one_step, k.tonight?.stretch, ...k.cousins].filter(
              (c): c is NonNullable<typeof c> => Boolean(c),
            ),
          )}
          onChange={(have) => k.setPrefs({ ...k.prefs, have })}
        />
      </div>

      {k.error && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 text-sm text-destructive"
        >
          <span>{k.error}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => k.setPrefs(k.prefs)}
          >
            Try again
          </Button>
        </div>
      )}

      <div
        role="tablist"
        aria-label="View"
        className="grid grid-cols-2 rounded-xl bg-muted p-1"
      >
        {(["suggestions", "map"] as const).map((v) => (
          <button
            key={v}
            type="button"
            role="tab"
            aria-selected={view === v}
            onClick={() => setView(v)}
            className={cn(
              "h-9 rounded-lg text-sm font-medium transition-colors",
              "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
              view === v
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground",
            )}
          >
            {v === "suggestions" ? "Suggestions" : "Map"}
          </button>
        ))}
      </div>

      {view === "map" && (
        <KitchenMap
          repertoire={repertoireOf(k.dishes, k.cooked)}
          diet={k.prefs.diet}
          have={k.prefs.have}
          isCooked={isCooked}
          onCooked={k.markCooked}
        />
      )}

      <div
        hidden={view !== "suggestions"}
        className={cn(
          "space-y-10 transition-opacity",
          k.updating && "opacity-60",
        )}
      >
        <Tonight
          picks={k.tonight}
          minutes={k.prefs.minutes}
          onMinutes={(minutes) => k.setPrefs({ ...k.prefs, minutes })}
          isCooked={isCooked}
          onCooked={k.markCooked}
          onSkip={k.skipTonight}
        />

        <section aria-labelledby="more" className="space-y-3">
          <h2
            id="more"
            className="font-heading text-xl font-semibold tracking-tight"
          >
            {more.length
              ? "More dishes you're close to"
              : "Nothing else close enough — try describing another dish."}
          </h2>
          {more.map((cousin, i) => (
            <CousinCard
              key={cousin.dish.id}
              cousin={cousin}
              index={i}
              cooked={isCooked(cousin.dish.id)}
              onCooked={() => k.markCooked(cousin.dish)}
            />
          ))}
        </section>

        <AccountCard variant="results" />
      </div>
    </div>
  );
}
