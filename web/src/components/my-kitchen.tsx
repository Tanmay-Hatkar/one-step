"use client";

import { ChevronRight, Heart } from "lucide-react";
import Link from "next/link";

import { AccountCard } from "@/components/account-card";
import { Filters } from "@/components/filters";
import { RepertoireSummary } from "@/components/repertoire-summary";
import { agoLabel } from "@/lib/cooklog";
import type { CookLogEntry, CookedDish, Prefs } from "@/lib/storage";
import type { UserDish } from "@/lib/types";

const LATELY = 6;

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="rounded-xl border bg-card px-3 py-3">
      <p className="font-heading text-3xl leading-none font-semibold tabular-nums">{value}</p>
      <p className="mt-1.5 text-xs leading-snug text-muted-foreground">{label}</p>
    </div>
  );
}

/** Everything about you: what you cook, what you've cooked lately, diet, pantry, account. */
export function MyKitchen({
  dishes,
  cooked,
  log,
  reach,
  savedCount,
  prefs,
  onPrefs,
  implied,
  suggested,
  shareable,
  onEdit,
  onReview,
  onRemoveCooked,
}: {
  dishes: UserDish[];
  cooked: CookedDish[];
  log: CookLogEntry[];
  reach: number | null;
  savedCount: number;
  prefs: Prefs;
  onPrefs: (prefs: Prefs) => void;
  implied: string[];
  suggested: string[];
  shareable: UserDish[];
  onEdit: () => void;
  onReview: () => void;
  onRemoveCooked: (id: string) => void;
}) {
  return (
    <div className="space-y-8">
      <h1 className="font-heading text-4xl leading-tight font-semibold tracking-tight">
        Your kitchen
      </h1>

      <div className="grid grid-cols-3 gap-2">
        <Stat value={dishes.length + cooked.length} label="dishes you cook" />
        <Stat value={cooked.length} label={cooked.length === 1 ? "new dish learned" : "new dishes learned"} />
        <Stat value={reach ?? "…"} label="one step away" />
      </div>

      <RepertoireSummary
        dishes={dishes}
        cooked={cooked}
        onEdit={onEdit}
        onReview={onReview}
        onRemoveCooked={onRemoveCooked}
        shareable={shareable}
      />

      <section aria-labelledby="lately" className="space-y-2">
        <h2 id="lately" className="text-sm font-medium text-muted-foreground">
          Cooked lately
        </h2>
        {log.length === 0 ? (
          <p className="rounded-xl border border-dashed px-4 py-3 text-sm text-muted-foreground">
            Tap <span className="font-medium text-foreground">I made this</span> when you cook.
            I&apos;ll keep track, and suggest the dish you haven&apos;t had for a while.
          </p>
        ) : (
          <ul className="divide-y rounded-xl border bg-card">
            {log.slice(0, LATELY).map((entry) => (
              <li key={`${entry.name}-${entry.at}`} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                <span className="truncate font-medium">{entry.name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {agoLabel(new Date(entry.at))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Link
        href="/saved"
        className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <Heart aria-hidden className="size-5 text-primary" />
        <span className="flex-1">
          <span className="block font-medium">Saved and shopping list</span>
          <span className="block text-xs text-muted-foreground">
            {savedCount ? `${savedCount} saved` : "Dishes you save go on one list"}
          </span>
        </span>
        <ChevronRight aria-hidden className="size-4 text-muted-foreground" />
      </Link>

      <section aria-labelledby="about-you" className="space-y-2">
        <h2 id="about-you" className="text-sm font-medium text-muted-foreground">
          Diet and what you have
        </h2>
        <Filters prefs={prefs} onPrefs={onPrefs} implied={implied} suggested={suggested} showTime={false} />
      </section>

      <AccountCard variant="results" />
    </div>
  );
}
