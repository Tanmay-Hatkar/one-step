"use client";

import { Check, Share2 } from "lucide-react";
import { useState } from "react";

const PASTED_PREFIX = "pasted_";

/**
 * "I just cooked Mesir Wat": shares the dish's public page (it has a picture preview)
 * through the phone's share sheet, or copies the link. Only catalog dishes have a page.
 */
export function ShareCooked({ id, name }: { id: string; name: string }) {
  const [copied, setCopied] = useState(false);
  if (id.startsWith(PASTED_PREFIX)) return null;

  async function share() {
    const url = `${window.location.origin}/dish/${id}`;
    const text = `I just cooked ${name}, one step from what I already make.`;
    if (navigator.share) {
      try {
        await navigator.share({ title: name, text, url });
        return;
      } catch {
        // Dismissed or unavailable: fall back to copying.
      }
    }
    try {
      await navigator.clipboard.writeText(`${text} ${url}`);
      setCopied(true);
    } catch {
      // Clipboard blocked: nothing else to do.
    }
  }

  return (
    <button
      type="button"
      onClick={share}
      className="mt-1 inline-flex items-center gap-1 font-medium underline underline-offset-2"
    >
      {copied ? <Check aria-hidden className="size-3.5" /> : <Share2 aria-hidden className="size-3.5" />}
      {copied ? "Link copied" : "Share it"}
    </button>
  );
}
