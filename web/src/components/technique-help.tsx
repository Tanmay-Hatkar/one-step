"use client";

import { ChevronDown, ExternalLink, GraduationCap } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { getTechniques } from "@/lib/api";
import { techniqueLabel } from "@/lib/labels";
import type { TechniqueGuide } from "@/lib/types";
import { cn } from "@/lib/utils";

/** "How to: blooming whole spices" — a short guide that opens in place. */
export function TechniqueHelp({ technique }: { technique: string }) {
  const [open, setOpen] = useState(false);
  const [guide, setGuide] = useState<TechniqueGuide | null>(null);
  const [failed, setFailed] = useState(false);
  const bodyId = useId();

  useEffect(() => {
    if (!open || guide) return;
    let live = true;
    getTechniques()
      .then((all) => live && setGuide(all.find((g) => g.id === technique) ?? null))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [open, guide, technique]);

  return (
    <div className="rounded-lg border bg-background/60">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <GraduationCap aria-hidden className="size-4 shrink-0 text-primary" />
        <span className="flex-1">
          New skill: <span className="font-medium">{techniqueLabel(technique)}</span>
        </span>
        <span className="text-xs text-muted-foreground">How?</span>
        <ChevronDown
          aria-hidden
          className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>
      {open && (
        <div id={bodyId} className="space-y-2 px-3 pb-3 text-sm">
          {failed && <p className="text-muted-foreground">Couldn&apos;t load the guide.</p>}
          {!guide && !failed && <p className="text-muted-foreground">Loading…</p>}
          {guide && (
            <>
              <ol className="list-decimal space-y-1 pl-5 marker:text-muted-foreground">
                {guide.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              <p className="text-muted-foreground">
                <span className="font-medium text-foreground/80">Watch out: </span>
                {guide.tip}
              </p>
              <a
                href={`https://www.youtube.com/results?search_query=${encodeURIComponent(guide.watch_query)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"
              >
                Watch a short video
                <ExternalLink aria-hidden className="size-3.5" />
              </a>
            </>
          )}
        </div>
      )}
    </div>
  );
}
