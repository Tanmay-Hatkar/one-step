import type { Metadata } from "next";

import { SavedView } from "@/components/saved-view";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = {
  title: "Saved · One Step",
  description: "Dishes you saved for later, and one shopping list for all of them.",
};

export default function SavedPage() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-8 pb-16 sm:pt-12">
      <SavedView />
      <SiteFooter />
    </main>
  );
}
