"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";

/** Chrome/Edge/Android's install event (not in the DOM typings yet). */
interface InstallPrompt extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** "Install the app" — only where the browser offers it, and gone once installed. */
export function InstallApp() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);

  useEffect(() => {
    const offer = (e: Event) => {
      e.preventDefault(); // show our own button instead of the browser's mini-bar
      setPrompt(e as InstallPrompt);
    };
    const installed = () => setPrompt(null);
    window.addEventListener("beforeinstallprompt", offer);
    window.addEventListener("appinstalled", installed);
    return () => {
      window.removeEventListener("beforeinstallprompt", offer);
      window.removeEventListener("appinstalled", installed);
    };
  }, []);

  if (!prompt) return null;
  return (
    <button
      type="button"
      onClick={async () => {
        await prompt.prompt();
        await prompt.userChoice;
        setPrompt(null);
      }}
      className="mb-3 flex w-fit items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm text-foreground hover:bg-muted"
    >
      <Download aria-hidden className="size-3.5" />
      Install the app
    </button>
  );
}
