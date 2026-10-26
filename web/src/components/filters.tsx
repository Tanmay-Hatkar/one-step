"use client";

import { DietPicker } from "@/components/diet-picker";
import { ToggleChip } from "@/components/toggle-chip";
import { WhatIHave } from "@/components/what-i-have";
import type { Prefs } from "@/lib/storage";

const TIME_OPTIONS: { minutes: number | null; label: string }[] = [
  { minutes: null, label: "Any time" },
  { minutes: 30, label: "30 min" },
  { minutes: 60, label: "1 hour" },
  { minutes: 120, label: "2 hours" },
];

/** How many filters are narrowing the results, for the button's badge. */
export function activeFilterCount(prefs: Prefs): number {
  return (
    (prefs.minutes !== null ? 1 : 0) +
    (prefs.diet.vegetarian ? 1 : 0) +
    prefs.diet.avoid.length +
    prefs.have.equipment.length +
    prefs.have.ingredients.length
  );
}

/** Everything that narrows the results, in one place instead of spread over the page. */
export function Filters({
  prefs,
  onPrefs,
  implied,
  suggested,
}: {
  prefs: Prefs;
  onPrefs: (prefs: Prefs) => void;
  implied: string[];
  suggested: string[];
}) {
  return (
    <div className="space-y-5 rounded-xl border bg-card p-4">
      <div className="space-y-2">
        <p className="text-sm font-medium">Time you have</p>
        <div role="group" aria-label="Time you have" className="flex flex-wrap gap-2">
          {TIME_OPTIONS.map((o) => (
            <ToggleChip
              key={o.label}
              pressed={prefs.minutes === o.minutes}
              onClick={() => onPrefs({ ...prefs, minutes: o.minutes })}
            >
              {o.label}
            </ToggleChip>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Diet &amp; allergies</p>
        <DietPicker diet={prefs.diet} onChange={(diet) => onPrefs({ ...prefs, diet })} />
      </div>
      <WhatIHave
        have={prefs.have}
        implied={implied}
        suggested={suggested}
        onChange={(have) => onPrefs({ ...prefs, have })}
      />
    </div>
  );
}
