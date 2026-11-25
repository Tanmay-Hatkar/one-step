"use client";

import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import type { Recipe } from "@/lib/types";

/** Keep the screen on while cooking, where the browser allows it. */
function useWakeLock(on: boolean) {
  useEffect(() => {
    if (!on || !("wakeLock" in navigator)) return;
    let lock: WakeLockSentinel | null = null;
    const take = () => {
      navigator.wakeLock
        .request("screen")
        .then((l) => (lock = l))
        .catch(() => {});
    };
    take();
    // The lock drops when the tab is hidden; take it again on return.
    const again = () => document.visibilityState === "visible" && take();
    document.addEventListener("visibilitychange", again);
    return () => {
      document.removeEventListener("visibilitychange", again);
      lock?.release().catch(() => {});
    };
  }, [on]);
}

/**
 * One step at a time, in big type, with the screen kept on. Page 0 is the ingredients,
 * so you can gather everything first.
 */
export function CookMode({ name, recipe, onClose }: { name: string; recipe: Recipe; onClose: () => void }) {
  const [page, setPage] = useState(0);
  const last = recipe.steps.length;
  useWakeLock(true);

  useEffect(() => {
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") setPage((p) => Math.min(p + 1, last));
      if (e.key === "ArrowLeft") setPage((p) => Math.max(p - 1, 0));
    };
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, [last, onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Cooking ${name}`}
      className="fixed inset-0 z-50 flex flex-col bg-background"
    >
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <p className="truncate font-heading text-lg font-semibold">{name}</p>
          <p className="text-xs text-muted-foreground">
            {page === 0 ? "Get these ready" : `Step ${page} of ${last}`}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close cook mode">
          <X aria-hidden />
        </Button>
      </header>
      <div aria-hidden className="h-1 bg-muted">
        <div className="h-full bg-primary transition-all" style={{ width: `${(page / last) * 100}%` }} />
      </div>

      <div aria-live="polite" className="flex-1 overflow-y-auto px-5 py-8">
        {page === 0 ? (
          <ul className="mx-auto max-w-xl space-y-3 text-xl leading-snug">
            {recipe.ingredients.map((item, i) => (
              <li key={`${i}-${item}`} className="flex gap-3">
                <span aria-hidden className="mt-3 size-2 shrink-0 rounded-full bg-primary" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mx-auto max-w-xl text-2xl leading-relaxed sm:text-3xl">{recipe.steps[page - 1]}</p>
        )}
      </div>

      <footer className="grid grid-cols-2 gap-3 border-t px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Button
          variant="outline"
          size="lg"
          className="h-14 text-base"
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
        >
          <ArrowLeft aria-hidden />
          Back
        </Button>
        {page < last ? (
          <Button size="lg" className="h-14 text-base" onClick={() => setPage((p) => p + 1)}>
            {page === 0 ? "Start cooking" : "Next"}
            <ArrowRight aria-hidden />
          </Button>
        ) : (
          <Button size="lg" className="h-14 text-base" onClick={onClose}>
            Done
          </Button>
        )}
      </footer>
    </div>
  );
}
