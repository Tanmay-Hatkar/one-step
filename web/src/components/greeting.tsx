"use client";

import { Check, X } from "lucide-react";
import { useState, useSyncExternalStore } from "react";

import { MAX_NAME_CHARS, partOfDay, useName } from "@/lib/profile";

const noop = () => () => {};
/** The hour on this device; -1 while rendering on the server. */
const useHour = () =>
  useSyncExternalStore(noop, () => new Date().getHours(), () => -1);

const WEEKDAY = new Intl.DateTimeFormat(undefined, { weekday: "long" });

/**
 * "Good evening, Tanmay." at the top of the app. The name is optional, asked for in place,
 * and stays on this device.
 */
export function Greeting({ subtitle }: { subtitle: string }) {
  const [name, setName] = useName();
  const hour = useHour();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const part = hour < 0 ? null : partOfDay(hour);
  const hello = part ? `Good ${part}` : "Hello";

  function startEditing() {
    setDraft(name);
    setEditing(true);
  }

  function save(e: React.FormEvent) {
    e.preventDefault();
    setName(draft);
    setEditing(false);
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-primary" suppressHydrationWarning>
        {part ? `${WEEKDAY.format(new Date())} ${part}` : " "}
      </p>
      <h1 className="font-heading text-4xl leading-[1.08] font-semibold tracking-tight text-balance">
        {hello}
        {name ? (
          <>
            ,{" "}
            <button
              type="button"
              onClick={startEditing}
              aria-label={`Change your name (${name})`}
              className="inline rounded-md text-left decoration-muted-foreground/40 decoration-dotted underline-offset-[6px] hover:underline focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              {name}
            </button>
          </>
        ) : null}
        .
      </h1>
      <p className="text-[15px] text-muted-foreground">{subtitle}</p>

      {editing ? (
        <form onSubmit={save} className="flex items-center gap-2 pt-1">
          <label htmlFor="your-name" className="sr-only">
            Your first name
          </label>
          <input
            id="your-name"
            autoFocus
            autoComplete="given-name"
            maxLength={MAX_NAME_CHARS}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Your first name"
            className="h-10 min-w-0 flex-1 rounded-lg border bg-card px-3 text-base outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <button
            type="submit"
            aria-label="Save name"
            className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            <Check aria-hidden className="size-4" />
          </button>
          <button
            type="button"
            aria-label="Cancel"
            onClick={() => setEditing(false)}
            className="flex size-10 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground"
          >
            <X aria-hidden className="size-4" />
          </button>
        </form>
      ) : (
        !name && (
          <button
            type="button"
            onClick={startEditing}
            className="text-sm text-muted-foreground underline decoration-dotted underline-offset-4 hover:text-foreground"
          >
            What should I call you?
          </button>
        )
      )}
      {editing && (
        <p className="text-xs text-muted-foreground">Only kept on this device. Never sent anywhere.</p>
      )}
    </div>
  );
}
