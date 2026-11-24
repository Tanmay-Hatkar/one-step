"use client";

import { ArrowLeft, Check, Copy, Heart, Share2, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DishPhoto } from "@/components/dish-photo";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  clearBought,
  shoppingList,
  toggleBought,
  toggleSaved,
  useSaved,
  type SavedDish,
  type ShoppingItem,
} from "@/lib/saved";
import { track } from "@/lib/track";
import { STARTER_DISHES } from "@/lib/starters";
import type { Dish } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The list as plain text, for WhatsApp, notes or a message. */
function listText(items: ShoppingItem[]): string {
  const lines = items.map((i) => `• ${i.item}${i.use ? ` (optional, or use ${i.use})` : ""}`);
  return `Shopping list (One Step)\n${lines.join("\n")}`;
}

/** One line under a saved dish: what to buy, or that stand-ins cover it. */
function needsLine(s: SavedDish): string {
  if (s.toBuy.length) return `Needs ${s.toBuy.slice(0, 3).join(", ")}${s.toBuy.length > 3 ? "…" : ""}`;
  const n = s.optional?.length ?? 0;
  if (n) return `Nothing new to buy · ${n} optional`;
  return "Nothing new to buy";
}

/** Saved dishes, and one shopping list for all of them. */
export function SavedView() {
  const { saved, bought } = useSaved();
  const [copied, setCopied] = useState(false);
  const items = shoppingList(saved);
  const toGet = items.filter((i) => !bought.includes(i.item));

  async function share() {
    const text = listText(toGet);
    track("shopping_shared");
    if (navigator.share) {
      try {
        await navigator.share({ text });
        return;
      } catch {
        // Cancelled, or not allowed here: fall back to copying.
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
    }
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft aria-hidden className="size-4" />
          One Step
        </Link>
        <h1 className="font-heading text-3xl font-semibold tracking-tight">Saved</h1>
      </header>

      {saved.length === 0 ? (
        <div className="space-y-3 rounded-xl border border-dashed p-6 text-center">
          <Heart aria-hidden className="mx-auto size-6 text-muted-foreground" />
          <p className="font-medium">Nothing saved yet</p>
          <p className="text-sm text-muted-foreground">
            Tap <span className="font-medium text-foreground">Save</span> on any dish to keep it
            here. Its ingredients go on one shopping list.
          </p>
          <Button nativeButton={false} render={<Link href="/" />} variant="outline">
            Find dishes
          </Button>
        </div>
      ) : (
        <>
          <section aria-labelledby="dishes" className="space-y-3">
            <h2 id="dishes" className="sr-only">
              Saved dishes
            </h2>
            <ul className="space-y-2">
              {saved.map((s) => (
                <li key={s.id}>
                  <Card className="flex-row items-center gap-3 px-3 py-3">
                    <DishPhoto id={s.id} name="" size={64} className="size-14 shrink-0 rounded-lg" />
                    <Link href={`/dish/${s.id}`} className="min-w-0 flex-1">
                      <p className="truncate font-medium">{s.name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {needsLine(s)}
                      </p>
                    </Link>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove ${s.name} from Saved`}
                      onClick={() =>
                        toggleSaved({ id: s.id, name: s.name } as Dish, null)
                      }
                      className="text-muted-foreground"
                    >
                      <X aria-hidden />
                    </Button>
                  </Card>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="shopping" className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h2 id="shopping" className="font-heading text-2xl font-semibold tracking-tight">
                Shopping list
              </h2>
              {bought.length > 0 && (
                <Button variant="ghost" size="sm" onClick={clearBought}>
                  Untick all
                </Button>
              )}
            </div>
            {items.length === 0 ? (
              <p className="text-sm text-muted-foreground">You have everything these dishes need.</p>
            ) : (
              <>
                <ul className="divide-y rounded-xl border bg-card">
                  {items.map(({ item, for: dishes, use }) => {
                    const done = bought.includes(item);
                    return (
                      <li key={item}>
                        <button
                          type="button"
                          role="checkbox"
                          aria-checked={done}
                          onClick={() => toggleBought(item)}
                          className="flex w-full items-center gap-3 px-4 py-3 text-left focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                        >
                          <span
                            aria-hidden
                            className={cn(
                              "grid size-5 shrink-0 place-items-center rounded-md border-2",
                              done ? "border-primary bg-primary text-primary-foreground" : "border-border",
                            )}
                          >
                            {done && <Check className="size-3.5" strokeWidth={3} />}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className={cn("block", done && "text-muted-foreground line-through")}>
                              {item}
                            </span>
                            <span className="block truncate text-xs text-muted-foreground">
                              {use ? `Optional, or use your ${use} · ` : ""}for {dishes.join(", ")}
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
                <Button onClick={share} disabled={!toGet.length} className="h-10 w-full sm:w-auto">
                  {copied ? <Check aria-hidden /> : typeof navigator !== "undefined" && "share" in navigator ? <Share2 aria-hidden /> : <Copy aria-hidden />}
                  {copied ? "Copied" : `Share list (${toGet.length})`}
                </Button>
              </>
            )}
          </section>
        </>
      )}

      {saved.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Popular to start with: {STARTER_DISHES.slice(0, 3).map((d) => d.name).join(", ")}.
        </p>
      )}
    </div>
  );
}
