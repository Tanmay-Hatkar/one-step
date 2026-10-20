import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { techniqueLabel } from "@/lib/labels";
import type { UserDish } from "@/lib/types";

export function RepertoireSummary({
  dishes,
  onEdit,
}: {
  dishes: UserDish[];
  onEdit: () => void;
}) {
  return (
    <section aria-labelledby="your-kitchen" className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 id="your-kitchen" className="text-sm font-medium text-muted-foreground">
          What you already cook
        </h2>
        <Button variant="ghost" size="sm" onClick={onEdit}>
          <Pencil aria-hidden />
          Edit
        </Button>
      </div>
      <ul className="flex flex-wrap gap-2">
        {dishes.map((dish) => (
          <li
            key={dish.name}
            className="rounded-xl border bg-card px-3 py-2 text-sm shadow-xs"
          >
            <span className="font-medium">{dish.name}</span>
            <span className="block text-xs text-muted-foreground">
              {dish.techniques.slice(0, 3).map(techniqueLabel).join(" · ")}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
