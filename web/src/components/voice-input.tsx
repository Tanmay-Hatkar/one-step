"use client";

import { Check, LoaderCircle, Mic, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, transcribe } from "@/lib/api";
import { formatClock } from "@/lib/labels";
import { useRecorder } from "@/lib/use-recorder";

/** Long enough to describe a few dishes; short enough to stay cheap (about $0.005). */
export const MAX_RECORDING_SECONDS = 90;

/** Bar heights relative to the voice level, so the meter looks like a little waveform. */
const BAR_SHAPE = [0.45, 0.8, 1, 0.7, 0.5];

/** Tap, talk about your cooking, and the words land in the text box. */
export function VoiceInput({
  onText,
  disabled,
}: {
  onText: (text: string) => void;
  disabled?: boolean;
}) {
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heard, setHeard] = useState(false);

  async function handleClip(clip: Blob) {
    setTranscribing(true);
    try {
      onText(await transcribe(clip));
      setHeard(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't hear that. Please try again.");
    } finally {
      setTranscribing(false);
    }
  }

  const recorder = useRecorder({ maxSeconds: MAX_RECORDING_SECONDS, onClip: handleClip });
  if (!recorder.supported) return null;

  const shownError = recorder.error ?? error;
  const recording = recorder.state === "recording";

  return (
    <div className="space-y-2">
      {recording ? (
        <div className="flex items-center gap-3 rounded-xl border border-primary/40 bg-primary/5 px-3 py-2">
          <span aria-hidden className="relative flex size-3 shrink-0">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-destructive/60" />
            <span className="relative inline-flex size-3 rounded-full bg-destructive" />
          </span>
          <span aria-hidden className="flex h-6 items-center gap-0.5">
            {BAR_SHAPE.map((shape, i) => (
              <span
                key={i}
                className="w-1 rounded-full bg-primary transition-[height] duration-75"
                style={{ height: `${Math.max(15, recorder.level * shape * 100)}%` }}
              />
            ))}
          </span>
          <span className="min-w-0 flex-1 text-sm whitespace-nowrap">
            Listening…{" "}
            <span className="text-muted-foreground tabular-nums">
              {formatClock(recorder.seconds)}
            </span>
          </span>
          <Button size="sm" onClick={recorder.stop} className="h-8">
            <Check aria-hidden />
            Done
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={recorder.cancel}
            aria-label="Cancel recording"
            className="size-8 text-muted-foreground"
          >
            <X aria-hidden />
          </Button>
        </div>
      ) : (
        <Button
          variant="outline"
          size="lg"
          onClick={() => {
            setError(null);
            setHeard(false);
            recorder.clearError();
            void recorder.start();
          }}
          disabled={disabled || transcribing || recorder.state === "starting"}
          className="h-11 w-full bg-card text-base sm:w-auto sm:px-5"
        >
          {transcribing ? (
            <LoaderCircle aria-hidden className="animate-spin" />
          ) : (
            <Mic aria-hidden className="text-primary" />
          )}
          {transcribing ? "Writing it down…" : "Say it out loud"}
        </Button>
      )}

      <p aria-live="polite" className="text-xs text-muted-foreground">
        {recording
          ? `Tell me what goes in and how you cook it. Tap Done when you're finished (up to ${formatClock(MAX_RECORDING_SECONDS)}).`
          : heard && !transcribing
            ? "Got it. Check it reads right, then tap the button below."
            : null}
      </p>
      {shownError && (
        <p role="alert" className="text-sm text-destructive">
          {shownError}
        </p>
      )}
    </div>
  );
}
