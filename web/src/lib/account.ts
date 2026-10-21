// Optional sign-in with a passkey, so a kitchen follows you to other devices.
// No email or password: the passkey lives in your phone's password manager. Signed out,
// everything keeps working from this device alone.

import {
  browserSupportsWebAuthn,
  type PublicKeyCredentialCreationOptionsJSON,
  type PublicKeyCredentialRequestOptionsJSON,
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser";

import { ApiError, request } from "./api";
import type { SavedKitchen } from "./storage";

const TOKEN_KEY = "one-step:session";
const PUSH_DELAY_MS = 1500;

interface Options<T> {
  challenge_id: string;
  options: T;
}

interface KitchenSync {
  kitchen: SavedKitchen | null;
  updated_at: string | null;
}

export function passkeysSupported(): boolean {
  return typeof window !== "undefined" && browserSupportsWebAuthn();
}

export function sessionToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function setToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Can't remember the sign-in; they'll just be asked again.
  }
  window.dispatchEvent(new Event("one-step:account"));
}

function authed(init: RequestInit = {}): RequestInit {
  return {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${sessionToken()}` },
  };
}

/** The browser's prompt was closed or timed out: not an error worth a red message. */
function cancelled(err: unknown): boolean {
  return (
    err instanceof Error &&
    (err.name === "NotAllowedError" || err.name === "AbortError")
  );
}

async function ceremony<T>(
  kind: "register" | "login",
  run: (options: T) => Promise<unknown>,
): Promise<boolean> {
  const start = await request<Options<T>>(`/api/auth/${kind}/options`, {
    method: "POST",
  });
  let credential: unknown;
  try {
    credential = await run(start.options);
  } catch (err) {
    if (cancelled(err)) return false;
    throw new ApiError("Your device couldn't use a passkey here.");
  }
  const { token } = await request<{ token: string }>(
    `/api/auth/${kind}/verify`,
    {
      method: "POST",
      body: JSON.stringify({ challenge_id: start.challenge_id, credential }),
    },
  );
  setToken(token);
  return true;
}

/** Create a passkey and an account, then upload this device's kitchen. False if cancelled. */
export async function saveWithPasskey(kitchen: SavedKitchen): Promise<boolean> {
  const ok = await ceremony<PublicKeyCredentialCreationOptionsJSON>(
    "register",
    (o) => startRegistration({ optionsJSON: o }),
  );
  if (ok) await pushKitchen(kitchen);
  return ok;
}

/**
 * Sign in with an existing passkey. The account's kitchen replaces this device's when it has
 * one; otherwise this device's kitchen is uploaded. Returns the kitchen to show, or null if
 * the prompt was cancelled.
 */
export async function signIn(
  local: SavedKitchen | null,
): Promise<SavedKitchen | "none" | null> {
  const ok = await ceremony<PublicKeyCredentialRequestOptionsJSON>(
    "login",
    (o) => startAuthentication({ optionsJSON: o }),
  );
  if (!ok) return null;
  const remote = await request<KitchenSync>("/api/kitchen", authed());
  if (remote.kitchen?.dishes?.length) return remote.kitchen;
  if (local?.dishes.length) await pushKitchen(local);
  return "none";
}

export async function signOut(): Promise<void> {
  const token = sessionToken();
  setToken(null);
  if (token)
    await request("/api/auth/logout", authed({ method: "POST" })).catch(
      () => {},
    );
}

export async function deleteAccount(): Promise<void> {
  await request("/api/me", authed({ method: "DELETE" }));
  setToken(null);
}

async function pushKitchen(kitchen: SavedKitchen): Promise<void> {
  try {
    await request(
      "/api/kitchen",
      authed({ method: "PUT", body: JSON.stringify({ kitchen }) }),
    );
    lastSynced = new Date();
    window.dispatchEvent(new Event("one-step:account"));
  } catch (err) {
    // Signed out elsewhere (or deleted): forget the token. Other failures retry on next save.
    if (err instanceof ApiError && err.status === 401) setToken(null);
  }
}

let pending: ReturnType<typeof setTimeout> | null = null;
let lastSynced: Date | null = null;

export function lastSyncedAt(): Date | null {
  return lastSynced;
}

/** Called on every local save: uploads shortly after the last change, if signed in. */
export function queueSync(kitchen: SavedKitchen): void {
  if (!sessionToken()) return;
  if (pending) clearTimeout(pending);
  pending = setTimeout(() => void pushKitchen(kitchen), PUSH_DELAY_MS);
}
