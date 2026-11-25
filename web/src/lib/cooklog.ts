// What you cooked and when. Pure helpers over the log kept in the saved kitchen.

import type { CookLogEntry } from "./storage";

/** Entries kept; older ones drop off. */
export const MAX_LOG = 200;
/** Names sent to the API. Mirrors max_recent_cooked in api/app/config.py. */
const MAX_RECENT = 40;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Dish names cooked lately, most recent first, each once. */
export function recentNames(log: CookLogEntry[]): string[] {
  return [...new Set(log.map((e) => e.name))].slice(0, MAX_RECENT);
}

/** When a dish was last cooked, if ever. */
export function lastCooked(log: CookLogEntry[], name: string): Date | null {
  const key = name.toLowerCase();
  const entry = log.find((e) => e.name.toLowerCase() === key);
  return entry ? new Date(entry.at) : null;
}

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/** Whole calendar days between a date and now (0 = today). */
export function daysAgo(when: Date, now = new Date()): number {
  return Math.round((startOfDay(now) - startOfDay(when)) / DAY_MS);
}

/** "today", "yesterday", "9 days ago", "3 weeks ago", "2 months ago" */
export function agoLabel(when: Date, now = new Date()): string {
  const days = daysAgo(when, now);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.round(days / 7)} weeks ago`;
  return `${Math.round(days / 30)} months ago`;
}

/** What was cooked today, newest first. */
export function cookedToday(log: CookLogEntry[], now = new Date()): CookLogEntry[] {
  return log.filter((e) => daysAgo(new Date(e.at), now) === 0);
}
