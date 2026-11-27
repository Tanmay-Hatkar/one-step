"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useState } from "react";

import { MAX_NAME_CHARS, useName } from "@/lib/profile";
import { type Theme, useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const THEMES: { id: Theme; label: string; Icon: typeof Sun }[] = [
  { id: "system", label: "Auto", Icon: Monitor },
  { id: "light", label: "Light", Icon: Sun },
  { id: "dark", label: "Dark", Icon: Moon },
];

/** Your name (for the greeting) and light/dark. Both stay on this device. */
export function YouSettings() {
  const [name, setName] = useName();
  const [theme, setTheme] = useTheme();
  const [draft, setDraft] = useState<string | null>(null);

  return (
    <section aria-labelledby="you" className="space-y-3">
      <h2 id="you" className="text-sm font-medium text-muted-foreground">
        You
      </h2>
      <div className="space-y-4 rounded-xl border bg-card p-4">
        <div className="space-y-1.5">
          <label htmlFor="settings-name" className="text-sm font-medium">
            What should I call you?
          </label>
          <input
            id="settings-name"
            autoComplete="given-name"
            maxLength={MAX_NAME_CHARS}
            value={draft ?? name}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              if (draft !== null) setName(draft);
              setDraft(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
            placeholder="Your first name"
            className="h-10 w-full rounded-lg border bg-background px-3 text-base outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <p className="text-xs text-muted-foreground">Only kept on this device.</p>
        </div>

        <div className="space-y-1.5">
          <p id="appearance" className="text-sm font-medium">
            Appearance
          </p>
          <div role="group" aria-labelledby="appearance" className="grid grid-cols-3 gap-1 rounded-xl bg-muted p-1">
            {THEMES.map(({ id, label, Icon }) => (
              <button
                key={id}
                type="button"
                aria-pressed={theme === id}
                onClick={() => setTheme(id)}
                className={cn(
                  "flex h-9 items-center justify-center gap-1.5 rounded-lg text-sm font-medium transition-colors",
                  "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                  theme === id ? "bg-background shadow-xs" : "text-muted-foreground",
                )}
              >
                <Icon aria-hidden className="size-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
