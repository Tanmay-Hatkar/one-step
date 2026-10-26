import { CousinCard } from "@/components/cousin-card";
import type { Dish, TonightPicks } from "@/lib/types";

/** The two picks for tonight: an easy switch first, then a bit of a stretch. */
export function Tonight({
  picks,
  isCooked,
  onCooked,
  onSkip,
}: {
  picks: TonightPicks | null;
  isCooked: (id: string) => boolean;
  onCooked: (dish: Dish) => void;
  onSkip: (key: string) => void;
}) {
  const nothing = picks && !picks.one_step && !picks.stretch;

  return (
    <section aria-labelledby="tonight" className="space-y-3">
      <h2 id="tonight" className="font-heading text-2xl font-semibold tracking-tight">
        Try tonight
      </h2>

      {!picks && <p className="text-sm text-muted-foreground">Picking something for tonight…</p>}
      {nothing && (
        <p className="text-sm text-muted-foreground">
          Nothing new fits your filters. Try giving yourself a little longer.
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
  );
}
