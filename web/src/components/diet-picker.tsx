import { Check, Leaf } from "lucide-react";

import { ToggleChip } from "@/components/toggle-chip";
import { ALLERGENS } from "@/lib/labels";
import type { Allergen, Diet } from "@/lib/types";

/** Vegetarian + allergens to avoid. These are hard filters, enforced by the API. */
export function DietPicker({ diet, onChange }: { diet: Diet; onChange: (diet: Diet) => void }) {
  function toggle(id: Allergen) {
    const avoid = diet.avoid.includes(id)
      ? diet.avoid.filter((a) => a !== id)
      : [...diet.avoid, id];
    onChange({ ...diet, avoid });
  }

  return (
    <div className="space-y-3">
      <ToggleChip
        pressed={diet.vegetarian}
        onClick={() => onChange({ ...diet, vegetarian: !diet.vegetarian })}
      >
        <Leaf aria-hidden className="size-3.5" />
        Vegetarian
      </ToggleChip>
      <div>
        <p className="mb-2 text-xs text-muted-foreground">Leave out</p>
        <div className="flex flex-wrap gap-2">
          {ALLERGENS.map(({ id, label }) => (
            <ToggleChip key={id} pressed={diet.avoid.includes(id)} onClick={() => toggle(id)}>
              {diet.avoid.includes(id) && <Check aria-hidden className="size-3.5" />}
              {label}
            </ToggleChip>
          ))}
        </div>
      </div>
    </div>
  );
}

/** "Vegetarian · no peanuts, dairy" — or "None" when nothing is set. */
export function dietSummary(diet: Diet): string {
  const parts: string[] = [];
  if (diet.vegetarian) parts.push("Vegetarian");
  if (diet.avoid.length) {
    const names = ALLERGENS.filter((a) => diet.avoid.includes(a.id)).map((a) =>
      a.label.toLowerCase(),
    );
    parts.push(`no ${names.join(", ")}`);
  }
  return parts.join(" · ") || "None";
}
