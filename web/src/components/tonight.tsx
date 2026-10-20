import { Home, X } from "lucide-react";

import { CousinCard } from "@/components/cousin-card";
import { ToggleChip } from "@/components/toggle-chip";
import { Button } from "@/components/ui/button";
import { techniqueLabel } from "@/lib/labels";
import type { Dish, TonightPicks } from "@/lib/types";

const TIME_OPTIONS: { minutes: number | null; label: string }[] = [
  { minutes: null, label: "Any time" },
  { minutes: 30, label: "30 min" },
  { minutes: 60, label: "1 hour" },
  { minutes: 120, label: "2 hours" },
];

export function Tonight({
  picks,
  minutes,
  onMinutes,
  isCooked,
  onCooked,
  onSkip,
}: {
  picks: TonightPicks | null;
  minutes: number | null;
  onMinutes: (minutes: number | null) => void;
  isCooked: (id: string) => boolean;
  onCooked: (dish: Dish) => void;
  onSkip: (key: string) => void;
}) {
  const nothing = picks && !picks.familiar && !picks.one_step && !picks.stretch;

  return (
    <section aria-labelledby="tonight" className="space-y-4">
      <div className="space-y-3">
        <h2 id="tonight" className="font-heading text-2xl font-semibold tracking-tight">
          Tonight
        </h2>
        <div role="group" aria-label="Time you have tonight" className="flex flex-wrap gap-2">
          {TIME_OPTIONS.map((o) => (
            <ToggleChip
              key={o.label}
              pressed={minutes === o.minutes}
              onClick={() => onMinutes(o.minutes)}
            >
              {o.label}
            </ToggleChip>
          ))}
        </div>
      </div>

      {!picks && <p className="text-sm text-muted-foreground">Picking something for tonight…</p>}
      {nothing && (
        <p className="text-sm text-muted-foreground">
          Nothing fits that time and diet. Try giving yourself a little longer.
        </p>
      )}

      {picks?.familiar && (
        <div className="flex items-start justify-between gap-3 rounded-xl border border-dashed bg-card/60 px-4 py-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Something familiar
            </p>
            <p className="mt-1 flex items-center gap-1.5 font-medium">
              <Home aria-hidden className="size-4 text-muted-foreground" />
              {picks.familiar.name}
            </p>
            <p className="text-xs text-muted-foreground">
              {picks.familiar.techniques.slice(0, 3).map(techniqueLabel).join(" · ")}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSkip(picks.familiar!.name)}
            className="text-muted-foreground"
            aria-label={`Not tonight: ${picks.familiar.name}`}
          >
            <X aria-hidden />
            Not tonight
          </Button>
        </div>
      )}

      {picks?.one_step && (
        <CousinCard
          key={picks.one_step.dish.id}
          cousin={picks.one_step}
          label="One step away"
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
          label="A stretch"
          cooked={isCooked(picks.stretch.dish.id)}
          onCooked={() => onCooked(picks.stretch!.dish)}
          onSkip={() => onSkip(picks.stretch!.dish.id)}
        />
      )}
    </section>
  );
}
