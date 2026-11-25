import Link from "next/link";

import { FeedbackButton } from "@/components/feedback-button";
import { InstallApp } from "@/components/install-app";

const LINK = "underline-offset-2 hover:text-foreground hover:underline";

/** Install, feedback, saved, legal, and the allergy note. */
export function SiteFooter() {
  return (
    <footer className="mt-16 space-y-3 text-xs text-muted-foreground">
      <InstallApp />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link href="/dishes" className={LINK}>
          Every dish
        </Link>
        <Link href="/saved" className={LINK}>
          Saved
        </Link>
        <Link href="/privacy" className={LINK}>
          Privacy
        </Link>
        <Link href="/terms" className={LINK}>
          Terms
        </Link>
        <FeedbackButton />
      </div>
      <p>
        Diet filters check each dish&apos;s ingredients, but suggestions are AI-assisted.
        Always check labels for allergies.
      </p>
    </footer>
  );
}
