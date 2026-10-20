import { Clock, Footprints, Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { equipmentLabel } from "@/lib/labels";
import type { Cousin } from "@/lib/types";

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function CousinCard({ cousin, index }: { cousin: Cousin; index: number }) {
  const { dish, delta, diff } = cousin;
  const [title, rest] = splitHeadline(diff.headline, dish.name);

  return (
    <Card
      className="animate-in fade-in slide-in-from-bottom-2 fill-mode-both duration-500"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground/80">{dish.cuisine}</span>
          <span aria-hidden>·</span>
          <span>{dish.region}</span>
        </div>
        <h3 className="font-heading text-2xl leading-tight font-semibold tracking-tight">
          {title}
          <span className="block text-base font-normal text-muted-foreground">{rest}</span>
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {delta.is_one_step && (
            <Badge>
              <Footprints aria-hidden />
              One step
            </Badge>
          )}
          <Badge variant="secondary">
            <Clock aria-hidden />
            {formatTime(dish.time_minutes)}
          </Badge>
          {dish.effort === "weekend" && <Badge variant="secondary">Weekend project</Badge>}
          {delta.new_equipment.map((item) => (
            <Badge key={item} variant="outline">
              <Wrench aria-hidden />
              Needs {equipmentLabel(item)}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <ul className="space-y-2">
          {diff.changes.map((change) => (
            <li key={change} className="flex gap-2.5 text-[15px] leading-snug">
              <span
                aria-hidden
                className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary"
              />
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
      </CardContent>
    </Card>
  );
}

/** "Kabsa: your chicken leg with rice, but…" → ["Kabsa", "your chicken leg with rice, but…"] */
function splitHeadline(headline: string, name: string): [string, string] {
  const prefix = `${name}: `;
  return headline.startsWith(prefix)
    ? [name, headline.slice(prefix.length)]
    : [name, headline];
}
