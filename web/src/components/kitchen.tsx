"use client";

import { CookingPot, Heart, List, Loader2, Map as MapIcon, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AccountCard } from "@/components/account-card";
import { ConfirmKitchen } from "@/components/confirm-kitchen";
import { CousinCard } from "@/components/cousin-card";
import { Hero } from "@/components/hero";
import { KitchenMap } from "@/components/kitchen-map";
import { LoadingCards } from "@/components/loading-cards";
import { MyKitchen } from "@/components/my-kitchen";
import { PasteRecipe } from "@/components/paste-recipe";
import { SiteFooter } from "@/components/site-footer";
import { StartForm } from "@/components/start-form";
import { TabBar, type Tab } from "@/components/tab-bar";
import { Tonight } from "@/components/tonight";
import { Button } from "@/components/ui/button";
import { getStats } from "@/lib/api";
import { impliedEquipment, oftenNeeded, repertoireOf } from "@/lib/kitchen";
import { captureShared } from "@/lib/pasted";
import { useSaved } from "@/lib/saved";
import type { DishStats } from "@/lib/types";
import { useKitchen } from "@/lib/use-kitchen";
import { useRecipeIds } from "@/lib/use-recipe-ids";
import { cn } from "@/lib/utils";

const TAB_KEY = "one-step:tab";
/** How long the "it's in your kitchen" message stays up. */
const NOTICE_MS = 9000;
const TABS: Tab[] = ["tonight", "explore", "bring", "kitchen"];

export function Kitchen() {
  const k = useKitchen();
  const [stats, setStats] = useState<DishStats | null>(null);
  const [tab, setTabState] = useState<Tab>("tonight");
  const [view, setView] = useState<"list" | "map">("list");
  const [shared, setShared] = useState(false);
  const recipeIds = useRecipeIds();
  const { saved } = useSaved();

  useEffect(() => {
    // A recipe shared to the app from another app waits here until there's a kitchen;
    // otherwise come back to the tab this browser tab was on.
    /* eslint-disable react-hooks/set-state-in-effect */
    const arrived = captureShared();
    setShared(arrived);
    try {
      const last = window.sessionStorage.getItem(TAB_KEY) as Tab | null;
      if (arrived) setTabState("bring");
      else if (last && TABS.includes(last)) setTabState(last);
    } catch {
      // Storage blocked: start on Tonight.
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  // The message after cooking floats above the tab bar and clears itself.
  const { notice, dismissNotice } = k;
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(dismissNotice, NOTICE_MS);
    return () => clearTimeout(timer);
  }, [notice, dismissNotice]);

  function setTab(next: Tab) {
    setTabState(next);
    window.scrollTo({ top: 0 });
    try {
      window.sessionStorage.setItem(TAB_KEY, next);
    } catch {
      // Not remembered; nothing else changes.
    }
  }

  const busy = k.phase === "reading" || k.phase === "finding";
  const isCooked = (id: string) => k.cooked.some((c) => c.id === id);
  const repertoire = repertoireOf(k.dishes, k.cooked);
  // Dishes with a full recipe first, so the top of the list never ends in a dead end.
  const explore = [...k.cousins].sort(
    (a, b) => Number(recipeIds.has(b.dish.id)) - Number(recipeIds.has(a.dish.id)),
  );

  if (k.phase === "confirm") {
    return (
      <>
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
        <SiteFooter />
      </>
    );
  }

  if (k.phase !== "results") {
    return (
      <>
        <Hero />
        <div className="space-y-8">
          {shared && !busy && (
            <p role="status" className="rounded-xl bg-accent px-4 py-3 text-sm text-accent-foreground">
              Got your recipe. First tell me a dish or two you already cook, then I&apos;ll show
              how it differs from yours.
            </p>
          )}
          <StartForm
            text={k.text}
            onText={k.setText}
            picked={k.picked}
            onToggle={k.togglePicked}
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
        <SiteFooter />
      </>
    );
  }

  return (
    <div className="space-y-6 pb-20">
      <header className="flex items-center gap-3">
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
        <Link
          href="/saved"
          className="ml-auto inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <Heart aria-hidden className="size-4" />
          Saved
          {saved.length > 0 && (
            <span className="rounded-full bg-accent px-1.5 text-xs text-accent-foreground tabular-nums">
              {saved.length}
            </span>
          )}
        </Link>
      </header>

      {k.notice && (
        <div
          role="status"
          className="fixed inset-x-0 bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-40 mx-auto flex w-[calc(100%-2rem)] max-w-[34rem] items-start gap-3 rounded-xl bg-accent px-4 py-3 text-sm text-accent-foreground shadow-lg ring-1 ring-foreground/5 animate-in fade-in slide-in-from-bottom-2"
        >
          <CookingPot aria-hidden className="mt-0.5 size-4 shrink-0" />
          <p className="flex-1">
            {k.notice.id ? (
              <>
                <span className="font-medium">{k.notice.name}</span> is in your kitchen now.{" "}
                {k.notice.unlocked > 0 ? (
                  <span className="font-medium">
                    {k.notice.unlocked} more {k.notice.unlocked === 1 ? "dish is" : "dishes are"}{" "}
                    now one step away.
                  </span>
                ) : (
                  "New dishes grow from it."
                )}
              </>
            ) : (
              <>
                Logged <span className="font-medium">{k.notice.name}</span> for today.
              </>
            )}
          </p>
          <button
            type="button"
            onClick={() =>
              k.notice!.id ? k.removeCooked(k.notice!.id) : k.undoMadeIt(k.notice!.name)
            }
            className="font-medium underline underline-offset-2"
          >
            Undo
          </button>
          <button type="button" onClick={k.dismissNotice} aria-label="Dismiss">
            <X aria-hidden className="size-4" />
          </button>
        </div>
      )}

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

      <div hidden={tab !== "tonight"} className={cn("transition-opacity", k.updating && "opacity-60")}>
        <Tonight
          picks={k.tonight}
          log={k.log}
          minutes={k.prefs.minutes}
          onMinutes={(minutes) => k.setPrefs({ ...k.prefs, minutes })}
          reach={k.reach}
          isCooked={isCooked}
          onCooked={k.markCooked}
          onMade={k.madeIt}
          onSkip={k.skipTonight}
          onExplore={() => setTab("explore")}
        />
      </div>

      {tab === "explore" && (
        <div className="space-y-5">
          <div className="space-y-1">
            <h1 className="font-heading text-4xl leading-tight font-semibold tracking-tight">
              Explore
            </h1>
            <p className="text-[15px] text-muted-foreground">
              {k.reach
                ? `${k.reach} dishes are one step from what you cook. Here are the closest.`
                : "Dishes close to what you already cook."}
            </p>
          </div>
          <div role="group" aria-label="View" className="grid grid-cols-2 gap-1 rounded-xl bg-muted p-1">
            {(["list", "map"] as const).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={view === v}
                onClick={() => setView(v)}
                className={cn(
                  "flex h-9 items-center justify-center gap-1.5 rounded-lg text-sm font-medium transition-colors",
                  "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                  view === v ? "bg-background shadow-xs" : "text-muted-foreground",
                )}
              >
                {v === "list" ? <List aria-hidden className="size-4" /> : <MapIcon aria-hidden className="size-4" />}
                {v === "list" ? "List" : "Map"}
              </button>
            ))}
          </div>
          {view === "map" ? (
            <KitchenMap
              repertoire={repertoire}
              diet={k.prefs.diet}
              have={k.prefs.have}
              isCooked={isCooked}
              onCooked={k.markCooked}
            />
          ) : (
            <section aria-label="Dishes you could make" className={cn("space-y-3 transition-opacity", k.updating && "opacity-60")}>
              {explore.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Nothing close enough yet. Add another dish you make in the Kitchen tab.
                </p>
              )}
              {explore.map((cousin, i) => (
                <CousinCard
                  key={cousin.dish.id}
                  cousin={cousin}
                  index={i}
                  cooked={isCooked(cousin.dish.id)}
                  onCooked={() => k.markCooked(cousin.dish)}
                />
              ))}
            </section>
          )}
        </div>
      )}

      {/* Kept mounted so a recipe being read isn't lost by switching tabs. */}
      <div hidden={tab !== "bring"}>
        <PasteRecipe
          repertoire={repertoire}
          diet={k.prefs.diet}
          have={k.prefs.have}
          isCooked={isCooked}
          onCooked={k.markCooked}
        />
      </div>

      {tab === "kitchen" && (
        <>
          <MyKitchen
            dishes={k.dishes}
            cooked={k.cooked}
            log={k.log}
            reach={k.reach}
            savedCount={saved.length}
            prefs={k.prefs}
            onPrefs={k.setPrefs}
            implied={impliedEquipment(repertoire)}
            suggested={oftenNeeded(
              [k.tonight?.one_step, k.tonight?.stretch, ...k.cousins].filter(
                (c): c is NonNullable<typeof c> => Boolean(c),
              ),
            )}
            shareable={repertoire}
            onEdit={k.edit}
            onReview={k.review}
            onRemoveCooked={k.removeCooked}
          />
          <SiteFooter />
        </>
      )}

      <TabBar tab={tab} onTab={setTab} />
    </div>
  );
}
