"use client";

import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** How long each step shows before the next one starts (the last one waits for the answer). */
const STEP_MS = 2200;

/**
 * What's happening while the first answer is worked out, as steps that tick off in the
 * order the work really happens, over skeleton cards. The last step stays until it's done.
 */
export function LoadingCards({ label, steps }: { label: string; steps?: string[] }) {
  const [at, setAt] = useState(0);
  const all = steps?.length ? steps : [label];

  useEffect(() => {
    if (at >= all.length - 1) return;
    const timer = setTimeout(() => setAt((i) => i + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [at, all.length]);

  return (
    <div className="space-y-4" role="status" aria-live="polite">
      <ol className="space-y-2">
        {all.map((step, i) => (
          <li
            key={step}
            className={cn(
              "flex items-center gap-2.5 text-sm transition-opacity duration-500",
              i > at && "opacity-0",
              i < at && "text-muted-foreground",
            )}
            aria-hidden={i > at}
          >
            {i < at ? (
              <Check aria-hidden className="size-4 text-primary" />
            ) : (
              <Loader2 aria-hidden className="size-4 animate-spin text-primary" />
            )}
            {step}
          </li>
        ))}
      </ol>
      {[0, 1].map((i) => (
        <div key={i} className="space-y-3 rounded-2xl border bg-card p-4">
          <div className="flex gap-3">
            <Skeleton className="size-20 shrink-0 rounded-xl" />
            <div className="flex-1 space-y-2 pt-1">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
      ))}
    </div>
  );
}
