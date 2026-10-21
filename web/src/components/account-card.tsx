"use client";

import { Check, KeyRound, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  deleteAccount,
  lastSyncedAt,
  passkeysSupported,
  saveWithPasskey,
  sessionToken,
  signIn,
  signOut,
} from "@/lib/account";
import { ApiError } from "@/lib/api";
import { loadKitchen, saveKitchen } from "@/lib/storage";

type Busy = "save" | "signin" | "signout" | "delete" | null;

function messageOf(err: unknown): string {
  return err instanceof ApiError
    ? err.message
    : "Something went wrong. Try again.";
}

/** Signed-in state, kept in step with sign-in/out anywhere on the page. */
function useAccount() {
  const [state, setState] = useState<{
    supported: boolean;
    signedIn: boolean;
    synced: Date | null;
  }>({ supported: false, signedIn: false, synced: null });
  useEffect(() => {
    const read = () =>
      setState({
        supported: passkeysSupported(),
        signedIn: Boolean(sessionToken()),
        synced: lastSyncedAt(),
      });
    read();
    window.addEventListener("one-step:account", read);
    return () => window.removeEventListener("one-step:account", read);
  }, []);
  return state;
}

/** Bring the account's kitchen onto this device and show it. */
async function signInAndLoad(): Promise<boolean> {
  const result = await signIn(loadKitchen());
  if (result === null) return false;
  if (result !== "none") {
    saveKitchen(result, { sync: false });
    window.location.reload();
  }
  return true;
}

/**
 * Optional passkey sign-in. On the start page: a quiet "sign in" for a second device.
 * On results: save this kitchen to a passkey, or manage the account once signed in.
 */
export function AccountCard({ variant }: { variant: "start" | "results" }) {
  const { supported, signedIn, synced } = useAccount();
  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (!supported) return null;

  async function run(kind: Busy, action: () => Promise<unknown>) {
    setBusy(kind);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(null);
    }
  }

  const errorLine = error && (
    <p role="alert" className="text-sm text-destructive">
      {error}
    </p>
  );

  if (variant === "start") {
    if (signedIn) return null;
    return (
      <div className="space-y-1 text-center text-sm text-muted-foreground">
        <p>
          Saved a kitchen on another device?{" "}
          <button
            type="button"
            onClick={() => run("signin", signInAndLoad)}
            disabled={busy !== null}
            className="inline-flex items-center gap-1 font-medium text-primary underline-offset-2 hover:underline"
          >
            {busy === "signin" && (
              <Loader2 aria-hidden className="size-3.5 animate-spin" />
            )}
            Sign in with your passkey
          </button>
        </p>
        {errorLine}
      </div>
    );
  }

  if (signedIn) {
    return (
      <div className="space-y-3 rounded-xl border bg-card px-4 py-3 text-sm">
        <p className="flex items-center gap-2">
          <Check aria-hidden className="size-4 text-primary" />
          <span>
            <span className="font-medium">Synced to your passkey.</span>{" "}
            <span className="text-muted-foreground">
              {synced
                ? `Saved ${synced.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}.`
                : "Changes save automatically."}{" "}
              Sign in on any device to see it.
            </span>
          </span>
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={busy !== null}
            onClick={() => run("signout", signOut)}
          >
            Sign out
          </Button>
          {confirmDelete ? (
            <Button
              variant="destructive"
              size="sm"
              disabled={busy !== null}
              onClick={() => run("delete", deleteAccount)}
            >
              {busy === "delete" && (
                <Loader2 aria-hidden className="animate-spin" />
              )}
              Yes, delete it from the server
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setConfirmDelete(true)}
            >
              Delete my account
            </Button>
          )}
        </div>
        {confirmDelete && (
          <p className="text-xs text-muted-foreground">
            Your kitchen stays on this device. You can then remove the passkey
            from your password manager.
          </p>
        )}
        {errorLine}
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-xl border bg-card px-4 py-3 text-sm">
      <div className="flex gap-3">
        <KeyRound aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
        <div className="space-y-0.5">
          <p className="font-medium">Keep this kitchen on all your devices</p>
          <p className="text-muted-foreground">
            Save it with a passkey: your face, fingerprint or screen lock. No
            email, no password.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Button
          size="sm"
          disabled={busy !== null}
          onClick={() =>
            run("save", async () => {
              const kitchen = loadKitchen();
              if (kitchen) await saveWithPasskey(kitchen);
            })
          }
        >
          {busy === "save" && <Loader2 aria-hidden className="animate-spin" />}
          Save with a passkey
        </Button>
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => run("signin", signInAndLoad)}
          className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          I already have one
        </button>
      </div>
      {errorLine}
    </div>
  );
}
