/** The public web address, for absolute links in share previews. */
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://one-step-six-brown.vercel.app";

/** The API, for server-side fetches (metadata). Same value the browser uses. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
