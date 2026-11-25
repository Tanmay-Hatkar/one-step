import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DishView } from "@/components/dish-view";
import { LoadingCards } from "@/components/loading-cards";
import { RelatedDishes } from "@/components/related-dishes";
import { SiteFooter } from "@/components/site-footer";
import { DishNotFound, fetchDishPage } from "@/lib/dish-data";
import { SITE_URL } from "@/lib/site";
import type { DishPage } from "@/lib/types";

const PASTED_PREFIX = "pasted_";

const FALLBACK: Metadata = {
  title: "A dish on One Step",
  description:
    "A home dish from around the world, written as a step from what you already cook.",
};

/** The catalog dish, or null when it should load in the browser (pasted, or API down). */
async function loadPage(id: string): Promise<DishPage | null> {
  if (id.startsWith(PASTED_PREFIX)) return null;
  try {
    return await fetchDishPage(id);
  } catch (err) {
    if (err instanceof DishNotFound) notFound();
    return null;
  }
}

export async function generateMetadata({
  params,
}: PageProps<"/dish/[id]">): Promise<Metadata> {
  const { id } = await params;
  const page = await loadPage(id);
  if (!page) return { ...FALLBACK, robots: { index: false } };
  const { dish, related = [] } = page;
  const title = `${dish.name} · One Step`;
  const nearby = related.slice(0, 3).map((r) => r.name);
  const description = nearby.length
    ? `${dish.summary} One step from ${nearby.join(", ")}.`
    : dish.summary;
  const image = { url: `/dishes/${id}.webp`, width: 512, height: 512, alt: dish.name };
  return {
    title,
    description,
    alternates: { canonical: `/dish/${id}` },
    openGraph: { title, description, images: [image], type: "article" },
    twitter: { card: "summary", title, description, images: [image] },
  };
}

/** schema.org Recipe, so search engines understand the page. Only facts we hold. */
function recipeJsonLd({ dish, recipe }: DishPage): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Recipe",
    name: dish.name,
    description: dish.summary,
    image: `${SITE_URL}/dishes/${dish.id}.webp`,
    recipeCuisine: dish.cuisine,
    totalTime: `PT${dish.time_minutes}M`,
    keywords: [dish.cuisine, dish.region, dish.family.replaceAll("_", " ")].join(", "),
    ...(dish.vegetarian && { suitableForDiet: "https://schema.org/VegetarianDiet" }),
    recipeIngredient: recipe?.ingredients ?? dish.key_ingredients,
    ...(recipe && {
      recipeInstructions: recipe.steps.map((text) => ({ "@type": "HowToStep", text })),
      isBasedOn: recipe.source_url,
      license: recipe.license_url,
    }),
  };
}

async function DishContent({ params }: { params: PageProps<"/dish/[id]">["params"] }) {
  const { id } = await params;
  const page = await loadPage(id);
  if (!page) return <DishView key={id} />;
  return (
    <>
      <script
        type="application/ld+json"
        // JSON.stringify output with "<" escaped cannot break out of the script tag.
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(recipeJsonLd(page)).replace(/</g, "\\u003c"),
        }}
      />
      <DishView key={page.dish.id} initial={page} />
      <div className="mt-10">
        <RelatedDishes name={page.dish.name} related={page.related ?? []} />
      </div>
    </>
  );
}

export default function DishRoute({ params }: PageProps<"/dish/[id]">) {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-8 pb-16 sm:pt-12">
      <Suspense fallback={<LoadingCards label="Opening the dish…" />}>
        <DishContent params={params} />
      </Suspense>
      <SiteFooter />
    </main>
  );
}
