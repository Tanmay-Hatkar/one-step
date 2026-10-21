"use client";

import { ArrowLeft, Clock, ExternalLink, Leaf } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CousinCard } from "@/components/cousin-card";
import { DishPhoto } from "@/components/dish-photo";
import { LoadingCards } from "@/components/loading-cards";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError, getCousin, getDishPage } from "@/lib/api";
import { repertoireOf } from "@/lib/kitchen";
import { ALLERGENS, formatTime } from "@/lib/labels";
import { loadKitchen } from "@/lib/storage";
import type { Cousin, DishPage } from "@/lib/types";

/** A catalog dish: photo, how it differs from your kitchen, and the full recipe. */
export function DishView() {
  const { id } = useParams<{ id: string }>();
  const [page, setPage] = useState<DishPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fromYours, setFromYours] = useState<Cousin | null>(null);

  useEffect(() => {
    let live = true;
    getDishPage(id)
      .then((p) => {
        if (!live) return;
        setPage(p);
        document.title = `${p.dish.name} · One Step`;
      })
      .catch((err) => live && setError(err instanceof ApiError ? err.message : "Couldn't load it."));

    // If they have a kitchen on this device, show this dish as a diff from it too.
    const saved = loadKitchen();
    if (saved?.dishes.length) {
      getCousin(repertoireOf(saved.dishes, saved.cooked), id, saved.prefs.diet, saved.prefs.have)
        .then((c) => live && setFromYours(c))
        .catch(() => {}); // already cooked, ruled out by diet, or offline: just skip it
    }
    return () => {
      live = false;
    };
  }, [id]);

  if (error) {
    return (
      <div className="space-y-4">
        <p role="alert" className="text-destructive">
          {error}
        </p>
        <Button nativeButton={false} render={<Link href="/" />} variant="outline">
          <ArrowLeft aria-hidden />
          Back to One Step
        </Button>
      </div>
    );
  }
  if (!page) return <LoadingCards label="Opening the dish…" />;

  const { dish, recipe } = page;
  const allergens = ALLERGENS.filter((a) => dish.allergens.includes(a.id)).map((a) => a.label);

  return (
    <article className="space-y-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden className="size-4" />
        One Step
      </Link>

      <header className="space-y-4">
        <figure className="space-y-1.5">
          <DishPhoto
            id={dish.id}
            name={dish.name}
            size={512}
            priority
            className="aspect-square w-full rounded-2xl"
          />
          <figcaption className="text-xs text-muted-foreground">
            Illustration (AI-generated), not a photo of this recipe.
          </figcaption>
        </figure>
        <div className="space-y-2">
          <h1 className="font-heading text-4xl leading-tight font-semibold tracking-tight">
            {dish.name}
          </h1>
          <p className="text-[15px] text-muted-foreground">{dish.summary}</p>
          <div className="flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
            <span className="font-medium text-foreground/80">{dish.cuisine}</span>
            <span aria-hidden>·</span>
            <span className="inline-flex items-center gap-1">
              <Clock aria-hidden className="size-3.5" />
              {formatTime(dish.time_minutes)}
            </span>
            {dish.effort === "weekend" && <Badge variant="secondary">Weekend</Badge>}
            {dish.vegetarian && (
              <Badge variant="outline">
                <Leaf aria-hidden />
                Vegetarian
              </Badge>
            )}
          </div>
          {allergens.length > 0 && (
            <p className="text-sm text-muted-foreground">Contains {allergens.join(", ").toLowerCase()}.</p>
          )}
        </div>
      </header>

      {fromYours && (
        <section aria-labelledby="from-yours" className="space-y-3">
          <h2 id="from-yours" className="font-heading text-xl font-semibold tracking-tight">
            From your kitchen
          </h2>
          <CousinCard cousin={fromYours} cooked={false} defaultOpen showRecipeLink={false} />
        </section>
      )}

      {recipe ? (
        <section aria-labelledby="recipe" className="space-y-5">
          <h2 id="recipe" className="font-heading text-2xl font-semibold tracking-tight">
            The full recipe
          </h2>
          <div className="space-y-2">
            <h3 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
              Ingredients
            </h3>
            <ul className="space-y-1.5 text-[15px]">
              {recipe.ingredients.map((item, i) => (
                <li key={`${i}-${item}`} className="flex gap-2.5">
                  <span aria-hidden className="mt-[9px] size-1.5 shrink-0 rounded-full bg-primary" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2">
            <h3 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
              Method
            </h3>
            <ol className="space-y-3 text-[15px] leading-relaxed">
              {recipe.steps.map((step, i) => (
                <li key={`${i}-${step}`} className="flex gap-3">
                  <span
                    aria-hidden
                    className="grid size-6 shrink-0 place-items-center rounded-full bg-accent text-xs font-semibold text-accent-foreground"
                  >
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
          <p className="border-t pt-3 text-xs text-muted-foreground">
            Recipe: &ldquo;
            <a href={recipe.source_url} className="underline underline-offset-2" rel="noopener">
              {recipe.title}
            </a>
            &rdquo; from the {recipe.source_name}, by {recipe.authors}, licensed{" "}
            <a href={recipe.license_url} className="underline underline-offset-2" rel="license noopener">
              {recipe.license}
            </a>
            . Lightly reformatted.
          </p>
        </section>
      ) : (
        <section className="space-y-2 rounded-xl border border-dashed p-4 text-sm">
          <p>No full recipe for this one here yet.</p>
          <a
            href={`https://www.google.com/search?q=${encodeURIComponent(`${dish.name} recipe`)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"
          >
            Search for a recipe
            <ExternalLink aria-hidden className="size-3.5" />
          </a>
        </section>
      )}
    </article>
  );
}
