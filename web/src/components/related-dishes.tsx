import Link from "next/link";

import { DishPhoto } from "@/components/dish-photo";
import { techniqueLabel } from "@/lib/labels";
import type { RelatedDish } from "@/lib/types";

function changeLine(related: RelatedDish): string {
  const parts: string[] = [];
  if (related.new_techniques.length) {
    const skills = related.new_techniques.map((t) => techniqueLabel(t).toLowerCase()).join(", ");
    parts.push(`New step: ${skills}`);
  }
  if (related.new_ingredients.length) parts.push(`add ${related.new_ingredients.join(", ")}`);
  return parts.length ? parts.join(" · ") : "Same method, different seasoning";
}

/** Server-rendered "one step from here" list: crawlable links between dishes, by cooking method. */
export function RelatedDishes({ name, related }: { name: string; related: RelatedDish[] }) {
  if (!related.length) return null;
  return (
    <section aria-labelledby="one-step-from" className="space-y-3">
      <h2 id="one-step-from" className="font-heading text-2xl font-semibold tracking-tight">
        If you can cook {name}, you&apos;re one step from…
      </h2>
      <p className="text-sm text-muted-foreground">
        Dishes made the same way, with only a few changes.
      </p>
      <ul className="space-y-2">
        {related.map((r) => (
          <li key={r.id}>
            <Link
              href={`/dish/${r.id}`}
              className="flex gap-3 rounded-xl border bg-card p-3 transition-colors hover:bg-accent/40"
            >
              <DishPhoto id={r.id} name={r.name} size={64} className="size-16 shrink-0 rounded-lg" />
              <span className="min-w-0 space-y-0.5">
                <span className="block font-medium">
                  {r.name} <span className="text-sm font-normal text-muted-foreground">· {r.cuisine}</span>
                </span>
                <span className="block text-sm text-muted-foreground">{changeLine(r)}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
