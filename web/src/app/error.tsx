"use client";

import { RotateCcw } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { reportError } from "@/components/error-tracking";
import { Button } from "@/components/ui/button";

/** Shown when a page crashes. Reports it, keeps the tone calm, offers a way back. */
export default function PageError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => reportError(error), [error]);

  return (
    <main className="mx-auto w-full max-w-xl space-y-6 px-4 pt-16 pb-16">
      <p className="text-sm font-medium tracking-wide text-primary">One Step</p>
      <h1 className="font-heading text-4xl leading-tight font-semibold tracking-tight">
        Something boiled over.
      </h1>
      <p className="text-muted-foreground">
        This page hit a snag. Your kitchen and saved dishes are safe on this device. We&apos;ve
        been told about it.
      </p>
      <div className="flex flex-wrap gap-3">
        <Button size="lg" onClick={reset} className="h-11 rounded-xl">
          <RotateCcw aria-hidden />
          Try again
        </Button>
        <Button
          size="lg"
          variant="outline"
          className="h-11 rounded-xl"
          nativeButton={false}
          render={<Link href="/" />}
        >
          Back to your kitchen
        </Button>
      </div>
    </main>
  );
}
