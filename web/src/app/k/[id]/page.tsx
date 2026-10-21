import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingCards } from "@/components/loading-cards";
import { SharedKitchenView } from "@/components/shared-kitchen";

import { API_URL } from "@/lib/site";

const FALLBACK: Metadata = {
  title: "A kitchen on One Step",
  description:
    "Dishes from around the world that are one step away from this kitchen.",
};

/** "A kitchen: dal and rice, chicken curry" for share previews. Snapshots never change. */
async function kitchenMetadata(id: string): Promise<Metadata> {
  "use cache";
  try {
    const response = await fetch(
      `${API_URL}/api/shares/${encodeURIComponent(id)}`,
    );
    if (!response.ok) return FALLBACK;
    const { dishes } = (await response.json()) as {
      dishes: { name: string }[];
    };
    const names = dishes.slice(0, 3).map((d) => d.name.toLowerCase());
    const description = `Someone who cooks ${names.join(", ")} shared their kitchen. See what's one step away.`;
    return {
      ...FALLBACK,
      description,
      openGraph: { title: FALLBACK.title ?? undefined, description },
    };
  } catch {
    return FALLBACK;
  }
}

export async function generateMetadata({
  params,
}: PageProps<"/k/[id]">): Promise<Metadata> {
  const { id } = await params;
  return kitchenMetadata(id);
}

export default function SharedKitchenPage() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-10 pb-16 sm:pt-16">
      {/* The id comes from the URL, so this part renders on request, not at build time. */}
      <Suspense fallback={<LoadingCards label="Opening the kitchen…" />}>
        <SharedKitchenView />
      </Suspense>
    </main>
  );
}
