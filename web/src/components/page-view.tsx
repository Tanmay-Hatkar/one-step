"use client";

import { useEffect } from "react";

import { trackOnce } from "@/lib/track";

/** Counts a visit (once per browser session, on whichever page it starts). */
export function PageView() {
  useEffect(() => trackOnce("landed"), []);
  return null;
}
