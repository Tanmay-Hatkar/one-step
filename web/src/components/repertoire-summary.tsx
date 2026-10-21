import { Check, ListChecks, Pencil, X } from "lucide-react";

import { ShareButton } from "@/components/share-button";
import { Button } from "@/components/ui/button";
import { techniqueLabel } from "@/lib/labels";
import type { CookedDish } from "@/lib/storage";
import type { UserDish } from "@/lib/types";

export function RepertoireSummary({
  dishes,
  cooked,
  onEdit,
  onReview,
  onRemoveCooked,
  shareable,
}: {
  dishes: UserDish[];
  cooked: CookedDish[];
  onEdit: () => void;
  /** Back to "Here's what I heard" to fix guesses and answer questions. */
  onReview: () => void;
  onRemoveCooked: (id: string) => void;
  /** Everything in the kitchen (own + cooked), for the share link. */
  shareable: UserDish[];
}) {
  return (
    <section aria-labelledby="your-kitchen" className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 id="your-kitchen" className="text-sm font-medium text-muted-foreground">
          Your kitchen
        </h2>
        <div className="flex items-start gap-1">
          <ShareButton dishes={shareable} />
          <Button variant="ghost" size="sm" onClick={onReview}>
            <ListChecks aria-hidden />
            Check
          </Button>
          <Button variant="ghost" size="sm" onClick={onEdit}>
            <Pencil aria-hidden />
            Edit
          </Button>
        </div>
      </div>
      <ul className="flex flex-wrap gap-2">
        {dishes.map((dish) => (
          <li key={dish.name} className="rounded-xl border bg-card px-3 py-2 text-sm shadow-xs">
            <span className="font-medium">{dish.name}</span>
            <span className="block text-xs text-muted-foreground">
              {dish.techniques.slice(0, 3).map(techniqueLabel).join(" · ")}
            </span>
          </li>
        ))}
        {cooked.map((c) => (
          <li
            key={c.id}
            className="flex items-center gap-1 rounded-xl border border-primary/30 bg-card py-1 pr-1 pl-3 text-sm shadow-xs"
          >
            <Check aria-hidden className="size-3.5 text-primary" />
            <span className="font-medium">{c.name}</span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => onRemoveCooked(c.id)}
              aria-label={`Remove ${c.name} from your kitchen`}
              className="text-muted-foreground"
            >
              <X aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
