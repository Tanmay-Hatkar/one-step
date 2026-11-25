import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/site-footer";
import { fetchDishIndex } from "@/lib/dish-data";
import type { DishIndexEntry } from "@/lib/types";

export const metadata: Metadata = {
  title: "Every dish · One Step",
  description:
    "Home dishes from around the world, each linked to the dishes you're one step away from by cooking method.",
  alternates: { canonical: "/dishes" },
};

function byRegion(dishes: DishIndexEntry[]): [string, DishIndexEntry[]][] {
  const groups = new Map<string, DishIndexEntry[]>();
  for (const d of dishes) groups.set(d.region, [...(groups.get(d.region) ?? []), d]);
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

/** A crawlable directory of every catalog dish, grouped by region. */
export default async function DishesPage() {
  const dishes = await fetchDishIndex();
  return (
    <main className="mx-auto w-full max-w-xl space-y-8 px-4 pt-8 pb-16 sm:pt-12">
      <header className="space-y-2">
        <Link href="/" className="text-sm font-medium text-primary">
          One Step
        </Link>
        <h1 className="font-heading text-4xl font-semibold tracking-tight">Every dish</h1>
        <p className="text-muted-foreground">
          {dishes.length > 0 ? `${dishes.length} home dishes` : "Home dishes"} from around the world.
          Open one to see the dishes it&apos;s one step from, or{" "}
          <Link href="/" className="text-primary underline-offset-2 hover:underline">
            tell One Step what you cook
          </Link>{" "}
          to see them as changes to your own cooking.
        </p>
      </header>
      {byRegion(dishes).map(([region, list]) => (
        <section key={region} aria-labelledby={`r-${region}`} className="space-y-2">
          <h2 id={`r-${region}`} className="font-heading text-xl font-semibold tracking-tight">
            {region}
          </h2>
          <ul className="grid grid-cols-1 gap-x-4 gap-y-1 text-[15px] sm:grid-cols-2">
            {list.map((d) => (
              <li key={d.id}>
                <Link href={`/dish/${d.id}`} className="underline-offset-2 hover:underline">
                  {d.name}
                </Link>{" "}
                <span className="text-sm text-muted-foreground">{d.cuisine}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      <SiteFooter />
    </main>
  );
}
