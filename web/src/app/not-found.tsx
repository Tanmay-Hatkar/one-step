import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = { title: "Not found · One Step" };

/** A link that leads nowhere: say so plainly and point somewhere useful. */
export default function NotFound() {
  return (
    <main className="mx-auto w-full max-w-xl space-y-6 px-4 pt-16 pb-16">
      <p className="text-sm font-medium tracking-wide text-primary">One Step</p>
      <h1 className="font-heading text-4xl leading-tight font-semibold tracking-tight">
        That one&apos;s not on the menu.
      </h1>
      <p className="text-muted-foreground">
        The link may be old, or the dish has moved. Here&apos;s where to go instead.
      </p>
      <ul className="space-y-2">
        <li>
          <Link
            href="/"
            className="block rounded-xl border bg-card px-4 py-3 font-medium hover:border-primary/50"
          >
            Find dishes one step from yours →
          </Link>
        </li>
        <li>
          <Link
            href="/dishes"
            className="block rounded-xl border bg-card px-4 py-3 font-medium hover:border-primary/50"
          >
            Browse every dish →
          </Link>
        </li>
      </ul>
      <SiteFooter />
    </main>
  );
}
