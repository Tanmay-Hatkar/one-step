import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingCards } from "@/components/loading-cards";
import { SharedKitchenView } from "@/components/shared-kitchen";

export const metadata: Metadata = {
  title: "A kitchen on One Step",
  description: "Dishes from around the world that are one step away from this kitchen.",
};

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
