"use client";

import { Check, ChevronDown, Clock, CookingPot, Mountain, Wrench, X } from "lucide-react";
import { useId, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { equipmentLabel, formatTime } from "@/lib/labels";
import type { Cousin } from "@/lib/types";
import { cn } from "@/lib/utils";

export function CousinCard({
  cousin,
  index = 0,
  label,
  defaultOpen = false,
  cooked,
  onCooked,
  onSkip,
}: {
  cousin: Cousin;
  index?: number;
  /** Small eyebrow above the title, e.g. "One step away". */
  label?: string;
  defaultOpen?: boolean;
  cooked: boolean;
  onCooked: () => void;
  /** Shown as "Not tonight" when set. */
  onSkip?: () => void;
}) {
  const { dish, delta, diff } = cousin;
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = useId();
  const [, rest] = splitHeadline(diff.headline, dish.name);

  return (
    <Card
      className="animate-in fade-in slide-in-from-bottom-2 gap-0 py-0 fill-mode-both duration-500"
      style={{ animationDelay: `${index * 70}ms` }}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((o) => !o)}
        className="w-full space-y-2 rounded-xl px-4 py-4 text-left focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        {label && (
          <p className="text-xs font-semibold tracking-wide text-primary uppercase">{label}</p>
        )}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-heading text-2xl leading-tight font-semibold tracking-tight">
              {dish.name}
            </h3>
            <p className="text-[15px] text-muted-foreground">{rest}</p>
          </div>
          <ChevronDown
            aria-hidden
            className={cn(
              "mt-1.5 size-5 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
          />
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground/80">{dish.cuisine}</span>
          <span aria-hidden>·</span>
          <span className="inline-flex items-center gap-1">
            <Clock aria-hidden className="size-3" />
            {formatTime(dish.time_minutes)}
          </span>
          {!delta.is_one_step && (
            <Badge variant="secondary" className="ml-1">
              <Mountain aria-hidden />
              Bigger step
            </Badge>
          )}
          {dish.effort === "weekend" && <Badge variant="secondary">Weekend</Badge>}
          {delta.new_equipment.map((item) => (
            <Badge key={item} variant="outline">
              <Wrench aria-hidden />
              Needs {equipmentLabel(item)}
            </Badge>
          ))}
          {cooked && (
            <Badge variant="outline" className="border-primary/40 text-primary">
              <Check aria-hidden />
              Cooked
            </Badge>
          )}
        </div>
      </button>

      {open && (
        <div id={bodyId} className="space-y-3 px-4 pb-4">
          <ul className="space-y-2">
            {diff.changes.map((change) => (
              <li key={change} className="flex gap-2.5 text-[15px] leading-snug">
                <span aria-hidden className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary" />
                <span>{change}</span>
              </li>
            ))}
          </ul>
          <p className="border-t pt-3 text-sm text-muted-foreground">{diff.keep_line}</p>
          {delta.new_ingredients.length > 0 && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground/70">You may need: </span>
              {delta.new_ingredients.join(", ")}
            </p>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              variant={cooked ? "secondary" : "default"}
              onClick={onCooked}
              disabled={cooked}
              className="h-9"
            >
              {cooked ? <Check aria-hidden /> : <CookingPot aria-hidden />}
              {cooked ? "In your kitchen" : "I cooked this"}
            </Button>
            {onSkip && (
              <Button variant="ghost" onClick={onSkip} className="h-9 text-muted-foreground">
                <X aria-hidden />
                Not tonight
              </Button>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

/** "Kabsa: your chicken leg with rice, but…" → ["Kabsa", "your chicken leg with rice, but…"] */
function splitHeadline(headline: string, name: string): [string, string] {
  const prefix = `${name}: `;
  return headline.startsWith(prefix) ? [name, headline.slice(prefix.length)] : [name, headline];
}
