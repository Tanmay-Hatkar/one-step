"use client";

import { Check, Share2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, createShare } from "@/lib/api";
import type { UserDish } from "@/lib/types";

/** Makes a read-only link to this kitchen; uses the phone's share sheet when there is one. */
export function ShareButton({ dishes }: { dishes: UserDish[] }) {
  const [state, setState] = useState<"idle" | "working" | "copied">("idle");
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function share() {
    setState("working");
    setError(null);
    try {
      const id = await createShare(dishes);
      const url = `${window.location.origin}/k/${id}`;
      setLink(url);
      if (navigator.share) {
        try {
          await navigator.share({ title: "My kitchen on One Step", url });
          setState("idle");
          return;
        } catch {
          // Share sheet dismissed or unavailable — fall back to copying.
        }
      }
      await navigator.clipboard.writeText(url);
      setState("copied");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : null);
      setState("idle");
    }
  }

  return (
    <div className="space-y-1">
      <Button variant="ghost" size="sm" onClick={share} disabled={state === "working"}>
        {state === "copied" ? <Check aria-hidden /> : <Share2 aria-hidden />}
        {state === "copied" ? "Link copied" : "Share"}
      </Button>
      {error && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
      {link && state !== "copied" && !error && (
        <p className="max-w-56 truncate text-xs text-muted-foreground">{link}</p>
      )}
    </div>
  );
}
