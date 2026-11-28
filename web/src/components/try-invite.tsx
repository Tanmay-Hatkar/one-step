import { ArrowRight } from "lucide-react";
import Link from "next/link";

/**
 * For someone who landed on a dish page (often from search) and hasn't told the app
 * what they cook: the one thing that makes this page personal.
 */
export function TryInvite({ dishName }: { dishName: string }) {
  return (
    <Link
      href="/"
      className="group block space-y-1.5 rounded-2xl bg-accent px-5 py-4 text-accent-foreground ring-1 ring-primary/15 transition-colors hover:ring-primary/40 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <p className="font-heading text-lg leading-snug font-semibold">
        How close is {dishName} to what you already cook?
      </p>
      <p className="text-sm">
        Tap the dishes you make and see this one, and others, written as just the changes.
      </p>
      <p className="inline-flex items-center gap-1 pt-1 text-sm font-semibold">
        Try it, no sign-up
        <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-0.5" />
      </p>
    </Link>
  );
}
