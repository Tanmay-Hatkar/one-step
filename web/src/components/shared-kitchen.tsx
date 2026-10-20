"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CousinCard } from "@/components/cousin-card";
import { KitchenMap } from "@/components/kitchen-map";
import { LoadingCards } from "@/components/loading-cards";
import { Button } from "@/components/ui/button";
import { ApiError, findCousins, getShare } from "@/lib/api";
import { techniqueLabel } from "@/lib/labels";
import { emptyKitchen, loadKitchen, saveKitchen } from "@/lib/storage";
import type { Cousin, UserDish } from "@/lib/types";

const NO_DIET = { vegetarian: false, avoid: [] };

/** Someone's shared kitchen, read-only, with a way to start from it. */
export function SharedKitchenView() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [dishes, setDishes] = useState<UserDish[] | null>(null);
  const [cousins, setCousins] = useState<Cousin[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasOwn, setHasOwn] = useState(false);

  useEffect(() => {
    /* eslint-disable-next-line react-hooks/set-state-in-effect */
    setHasOwn(Boolean(loadKitchen()?.dishes.length));
    getShare(id)
      .then(async (shared) => {
        setDishes(shared.dishes);
        setCousins(await findCousins(shared.dishes, NO_DIET));
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Couldn't open this kitchen."),
      );
  }, [id]);

  function useThisKitchen() {
    if (!dishes) return;
    if (hasOwn && !window.confirm("Replace your kitchen on this device with this one?")) return;
    saveKitchen({ ...emptyKitchen(), dishes, cousins: cousins ?? [] });
    router.push("/");
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Link href="/" className="text-sm font-medium tracking-wide text-primary">
          One Step
        </Link>
        <h1 className="font-heading text-3xl leading-tight font-semibold tracking-tight">
          Someone shared their kitchen with you
        </h1>
        <p className="text-muted-foreground">
          Here&apos;s what they cook, and the dishes from around the world that are one step
          away from it.
        </p>
      </header>

      {error && (
        <div role="alert" className="space-y-3">
          <p className="text-destructive">{error}</p>
          <Button nativeButton={false} render={<Link href="/" />}>Start your own kitchen</Button>
        </div>
      )}

      {dishes && (
        <section aria-labelledby="their-kitchen" className="space-y-3">
          <h2 id="their-kitchen" className="text-sm font-medium text-muted-foreground">
            Their kitchen
          </h2>
          <ul className="flex flex-wrap gap-2">
            {dishes.map((d) => (
              <li key={d.name} className="rounded-xl border bg-card px-3 py-2 text-sm shadow-xs">
                <span className="font-medium">{d.name}</span>
                <span className="block text-xs text-muted-foreground">
                  {d.techniques.slice(0, 3).map(techniqueLabel).join(" · ")}
                </span>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button onClick={useThisKitchen} className="h-10">
              Start from this kitchen
              <ArrowRight aria-hidden />
            </Button>
            <Button variant="outline" className="h-10" nativeButton={false} render={<Link href="/" />}>
              Describe my own
            </Button>
          </div>
        </section>
      )}

      {dishes && (
        <KitchenMap repertoire={dishes} diet={NO_DIET} isCooked={() => false} whose="their" />
      )}

      {dishes && !cousins && !error && <LoadingCards label="Finding dishes one step away…" />}
      {cousins && (
        <section aria-labelledby="close" className="space-y-3">
          <h2 id="close" className="font-heading text-xl font-semibold tracking-tight">
            Dishes they&apos;re close to
          </h2>
          {cousins.map((c, i) => (
            <CousinCard key={c.dish.id} cousin={c} index={i} defaultOpen={i === 0} cooked={false} />
          ))}
        </section>
      )}
    </div>
  );
}
