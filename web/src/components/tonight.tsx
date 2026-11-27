import { ArrowRight } from "lucide-react";

import { CousinCard } from "@/components/cousin-card";
import { Greeting } from "@/components/greeting";
import { OwnDishCard } from "@/components/own-dish-card";
import { ToggleChip } from "@/components/toggle-chip";
import { cookedToday, lastCooked } from "@/lib/cooklog";
import type { CookLogEntry } from "@/lib/storage";
import type { Dish, TonightPicks } from "@/lib/types";

const TIME_OPTIONS: { minutes: number | null; label: string }[] = [
  { minutes: null, label: "Any time" },
  { minutes: 30, label: "30 min" },
  { minutes: 60, label: "1 hour" },
];

/**
 * Tonight's answer: one of your own dishes (the one you haven't made for longest), an
 * easy switch beside it, and a stretch for a braver night.
 */
export function Tonight({
  picks,
  log,
  minutes,
  onMinutes,
  reach,
  isCooked,
  onCooked,
  onMade,
  onSkip,
  onExplore,
}: {
  picks: TonightPicks | null;
  log: CookLogEntry[];
  minutes: number | null;
  onMinutes: (minutes: number | null) => void;
  /** Dishes one step from the kitchen, when known. */
  reach: number | null;
  isCooked: (id: string) => boolean;
  onCooked: (dish: Dish) => void;
  /** One of the user's own dishes was cooked (by name). */
  onMade: (name: string) => void;
  onSkip: (key: string) => void;
  onExplore: () => void;
}) {
  const nothingNew = picks && !picks.one_step && !picks.stretch;
  const today = cookedToday(log);
  const familiar = picks?.familiar ?? null;
  const madeFamiliar = familiar ? today.some((e) => e.name === familiar.name) : false;
  // Until they've logged a dinner, lead with something new: that's what they came for.
  const newFirst = log.length === 0;

  const ownDish = familiar && (
    <section
      aria-labelledby={newFirst ? "your-usual" : undefined}
      aria-label={newFirst ? undefined : "From your kitchen"}
      className="space-y-3"
    >
      {newFirst && (
        <h2 id="your-usual" className="font-heading text-xl font-semibold tracking-tight">
          Or keep it easy
        </h2>
      )}
      <OwnDishCard
        key={familiar.name}
        dish={familiar}
        last={madeFamiliar ? null : lastCooked(log, familiar.name)}
        madeToday={madeFamiliar}
        onMade={() => onMade(familiar.name)}
        onSkip={() => onSkip(familiar.name)}
      />
    </section>
  );

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <Greeting subtitle="Here's what you could cook tonight." />
        <div role="group" aria-label="Time you have" className="flex flex-wrap gap-2 pt-2">
          {TIME_OPTIONS.map((o) => (
            <ToggleChip key={o.label} pressed={minutes === o.minutes} onClick={() => onMinutes(o.minutes)}>
              {o.label}
            </ToggleChip>
          ))}
        </div>
      </div>

      {!picks && <p className="text-sm text-muted-foreground">Picking something for tonight…</p>}

      {!newFirst && ownDish}

      <section aria-labelledby="one-step" className="space-y-3">
        <h2 id="one-step" className="font-heading text-xl font-semibold tracking-tight">
          {familiar && !newFirst ? "Or take one step" : "Something new, one step away"}
        </h2>
        {nothingNew && (
          <p className="text-sm text-muted-foreground">
            Nothing new fits that time. Try giving yourself a little longer.
          </p>
        )}
        {picks?.one_step && (
          <CousinCard
            key={picks.one_step.dish.id}
            cousin={picks.one_step}
            label="Easy switch"
            defaultOpen
            cooked={isCooked(picks.one_step.dish.id)}
            onCooked={() => onCooked(picks.one_step!.dish)}
            onSkip={() => onSkip(picks.one_step!.dish.id)}
          />
        )}
        {picks?.stretch && (
          <CousinCard
            key={picks.stretch.dish.id}
            cousin={picks.stretch}
            index={1}
            label="A bit of a stretch"
            cooked={isCooked(picks.stretch.dish.id)}
            onCooked={() => onCooked(picks.stretch!.dish)}
            onSkip={() => onSkip(picks.stretch!.dish.id)}
          />
        )}
      </section>

      {newFirst && ownDish}

      {reach !== null && reach > 0 && (
        <button
          type="button"
          onClick={onExplore}
          className="flex w-full items-center gap-3 rounded-xl bg-accent px-4 py-3 text-left text-accent-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <span className="font-heading text-3xl font-semibold tabular-nums">{reach}</span>
          <span className="flex-1 text-sm leading-snug">
            {reach === 1 ? "dish is" : "dishes are"} one step from your kitchen. Each one you
            cook opens more.
          </span>
          <ArrowRight aria-hidden className="size-4 shrink-0" />
        </button>
      )}
    </div>
  );
}
