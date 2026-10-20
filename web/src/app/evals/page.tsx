import type { Metadata } from "next";

import { EvalReport } from "@/components/eval-report";

export const metadata: Metadata = {
  title: "How well One Step works",
  description:
    "Public, automatically run checks on One Step's AI: reading your cooking, writing grounded differences, finding relevant dishes, and diet safety.",
};

export default function EvalsPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 pt-10 pb-16 sm:pt-16">
      <EvalReport />
    </main>
  );
}
