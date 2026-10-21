import type { Metadata } from "next";
import { Suspense } from "react";

import { DishView } from "@/components/dish-view";
import { LoadingCards } from "@/components/loading-cards";

export const metadata: Metadata = {
  title: "A dish on One Step",
  description: "A home dish from around the world, written as a step from what you already cook.",
};

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
