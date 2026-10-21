import type { Metadata } from "next";
import { Suspense } from "react";

import { DishView } from "@/components/dish-view";
import { LoadingCards } from "@/components/loading-cards";

import { API_URL } from "@/lib/site";

const FALLBACK: Metadata = {
  title: "A dish on One Step",
  description:
    "A home dish from around the world, written as a step from what you already cook.",
};

/** Title, summary and photo for share previews. Cached per dish; the catalog rarely changes. */
async function dishMetadata(id: string): Promise<Metadata> {
  "use cache";
  try {
    const response = await fetch(
      `${API_URL}/api/dishes/${encodeURIComponent(id)}`,
    );
    if (!response.ok) return FALLBACK;
    const { dish } = (await response.json()) as {
      dish: { name: string; summary: string; cuisine: string };
    };
    const title = `${dish.name} · One Step`;
    const image = {
      url: `/dishes/${id}.webp`,
      width: 512,
      height: 512,
      alt: dish.name,
    };
    return {
      title,
      description: dish.summary,
      openGraph: { title, description: dish.summary, images: [image] },
      twitter: {
        card: "summary",
        title,
        description: dish.summary,
        images: [image],
      },
    };
  } catch {
    return FALLBACK;
  }
}

export async function generateMetadata({
  params,
}: PageProps<"/dish/[id]">): Promise<Metadata> {
  const { id } = await params;
  return dishMetadata(id);
}

export default function DishPage() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-8 pb-16 sm:pt-12">
      {/* The id comes from the URL, so this part renders on request, not at build time. */}
      <Suspense fallback={<LoadingCards label="Opening the dish…" />}>
        <DishView />
      </Suspense>
    </main>
  );
}
