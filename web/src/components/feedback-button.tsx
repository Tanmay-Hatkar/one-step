"use client";

import { Loader2, MessageSquare } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { sendFeedback } from "@/lib/track";

const MAX = 2000;

/** "Send feedback": a small box that opens in place. Anonymous. */
export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  if (state === "sent") {
    return <p className="text-sm text-foreground">Thanks! I read every message.</p>;
  }
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 underline-offset-2 hover:text-foreground hover:underline"
      >
        <MessageSquare aria-hidden className="size-3.5" />
        Send feedback
      </button>
    );
  }

  async function send() {
    if (text.trim().length < 3) return;
    setState("sending");
    setError(null);
    try {
      await sendFeedback(text.trim());
      setState("sent");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't send. Try again.");
      setState("idle");
    }
  }

  return (
    <div className="w-full space-y-2">
      <Textarea
        aria-label="Your feedback"
        value={text}
        onChange={(e) => setText(e.target.value.slice(0, MAX))}
        placeholder="What was confusing, missing or great? No need to include your name."
        className="min-h-24 bg-card text-sm text-foreground"
        autoFocus
      />
      <div className="flex gap-2">
        <Button size="sm" onClick={send} disabled={state === "sending" || text.trim().length < 3}>
          {state === "sending" && <Loader2 aria-hidden className="animate-spin" />}
          Send
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
