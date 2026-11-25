import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/site-footer";

interface LegalPageProps {
  title: string;
  updated: string;
  children: ReactNode;
}

/** Shared shell for the privacy and terms pages: back link, title, plain prose. */
export function LegalPage({ title, updated, children }: LegalPageProps) {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-8 pb-16 sm:pt-12">
      <article className="space-y-8">
        <header className="space-y-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft aria-hidden className="size-4" />
            One Step
          </Link>
          <h1 className="font-heading text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="text-xs text-muted-foreground">Last updated {updated}</p>
        </header>
        <div className="space-y-6 text-[15px] leading-relaxed [&_h2]:font-heading [&_h2]:text-lg [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_section]:space-y-2 [&_ul]:space-y-1">
          {children}
        </div>
      </article>
      <SiteFooter />
    </main>
  );
}
