// A light buzz on phones that support it (Android browsers). Silently does nothing elsewhere.

/** Vibration patterns in ms: a tap, and a small "well done". */
const PATTERNS: Record<"tap" | "success", VibratePattern> = { tap: 8, success: [12, 60, 18] };

export function buzz(kind: keyof typeof PATTERNS = "tap"): void {
  try {
    if (typeof navigator !== "undefined" && "vibrate" in navigator) {
      navigator.vibrate(PATTERNS[kind]);
    }
  } catch {
    // Not supported or blocked: no buzz.
  }
}
