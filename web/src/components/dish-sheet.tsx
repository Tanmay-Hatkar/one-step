"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";

import { CousinCard } from "@/components/cousin-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Cousin } from "@/lib/types";

/** Bottom sheet showing one dish from the map. Closes on backdrop tap or Escape. */
export function DishSheet({
  cousin,
  loading,
  error,
  cooked,
  onCooked,
  onClose,
}: {
  cousin: Cousin | null;
  loading: boolean;
  error: string | null;
  cooked: boolean;
  onCooked?: () => void;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Dish details">
      <button
        type="button"
        aria-label="Close"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 bg-black/40 animate-in fade-in"
      />
      <div className="absolute inset-x-0 bottom-0 mx-auto max-h-[80vh] max-w-xl overflow-y-auto rounded-t-2xl bg-background p-4 pb-8 shadow-2xl animate-in slide-in-from-bottom-8">
        <div className="mb-2 flex justify-end">
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-full p-2 text-muted-foreground hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            <X aria-hidden className="size-5" />
          </button>
        </div>
        {loading && (
          <div className="space-y-3 rounded-xl border bg-card p-4" role="status" aria-live="polite">
            <p className="text-sm text-muted-foreground">Writing it up from your kitchen…</p>
            <Skeleton className="h-7 w-2/3" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
          </div>
        )}
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {cousin && (
          <CousinCard
            cousin={cousin}
            defaultOpen
            cooked={cooked}
            onCooked={onCooked}
          />
        )}
      </div>
    </div>
  );
}
