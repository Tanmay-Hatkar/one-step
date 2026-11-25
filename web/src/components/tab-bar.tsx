"use client";

import { ClipboardPaste, Compass, CookingPot, Utensils, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export type Tab = "tonight" | "explore" | "bring" | "kitchen";

const TABS: { id: Tab; label: string; icon: LucideIcon }[] = [
  { id: "tonight", label: "Tonight", icon: Utensils },
  { id: "explore", label: "Explore", icon: Compass },
  { id: "bring", label: "Bring", icon: ClipboardPaste },
  { id: "kitchen", label: "Kitchen", icon: CookingPot },
];

/** The four places in the app, fixed to the bottom like a phone app's tab bar. */
export function TabBar({
  tab,
  onTab,
  badges = {},
}: {
  tab: Tab;
  onTab: (tab: Tab) => void;
  /** A small count on a tab, e.g. pasted recipes waiting. */
  badges?: Partial<Record<Tab, number>>;
}) {
  return (
    <nav
      aria-label="Sections"
      className="fixed inset-x-0 bottom-0 z-40 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
    >
      <div className="mx-auto grid max-w-xl grid-cols-4 px-2 pb-[env(safe-area-inset-bottom)]">
        {TABS.map(({ id, label, icon: Icon }) => {
          const on = tab === id;
          const count = badges[id] ?? 0;
          return (
            <button
              key={id}
              type="button"
              aria-current={on ? "page" : undefined}
              onClick={() => onTab(id)}
              className={cn(
                "relative flex h-16 flex-col items-center justify-center gap-1 rounded-lg text-xs font-medium transition-colors",
                "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                on ? "text-primary" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <span
                className={cn(
                  "grid h-7 w-14 place-items-center rounded-full transition-colors",
                  on && "bg-accent",
                )}
              >
                <Icon aria-hidden className="size-5" strokeWidth={on ? 2.4 : 2} />
              </span>
              {label}
              {count > 0 && (
                <span className="absolute top-1.5 left-1/2 ml-3 rounded-full bg-primary px-1.5 text-[10px] leading-4 text-primary-foreground tabular-nums">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
