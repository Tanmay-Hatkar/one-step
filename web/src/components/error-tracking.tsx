"use client";

import { useEffect } from "react";

const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN ?? "";
const ENVIRONMENT = process.env.NEXT_PUBLIC_APP_ENV ?? "development";
const RELEASE = process.env.NEXT_PUBLIC_RELEASE ?? "dev";

/**
 * Starts browser error reporting when NEXT_PUBLIC_SENTRY_DSN is set.
 * The SDK is only downloaded in that case. No IPs, no request bodies, no replays.
 */
export function ErrorTracking() {
  useEffect(() => {
    if (!DSN) return;
    import("@sentry/browser")
      .then((Sentry) =>
        Sentry.init({
          dsn: DSN,
          environment: ENVIRONMENT,
          release: RELEASE,
          dataCollection: {
            userInfo: false,
            cookies: false,
            httpBodies: [],
            urlQueryParams: false,
            genAI: { inputs: false, outputs: false },
          },
          tracesSampleRate: 0,
        }),
      )
      .catch(() => {
        // Error tracking is best-effort; the app works without it.
      });
  }, []);
  return null;
}

/**
 * Report an error React caught (error boundaries swallow them, so the global handler
 * never sees them). Does nothing when error tracking is off.
 */
export function reportError(error: unknown): void {
  if (!DSN) return;
  import("@sentry/browser")
    .then((Sentry) => Sentry.captureException(error))
    .catch(() => {
      // Best-effort, like the rest of error tracking.
    });
}
