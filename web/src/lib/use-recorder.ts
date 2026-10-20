"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Formats the transcription API accepts, best first. Safari only does mp4. */
const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];

/** Normal speech has an RMS around 0.05–0.2; scale it to fill the meter. */
const LEVEL_GAIN = 7;

/** Shorter than this is almost always a mis-tap. */
const MIN_SECONDS = 1;

export type RecorderState = "idle" | "starting" | "recording";

function pickMimeType(): string | undefined {
  return MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t));
}

function micErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return "Microphone access is blocked. Allow it in your browser settings, or type instead.";
  }
  if (name === "NotFoundError") return "No microphone found. You can type instead.";
  return "Couldn't start the microphone. You can type instead.";
}

/**
 * Records one short clip from the microphone.
 * `level` (0–1) follows the voice so the user can see they're being heard.
 */
export function useRecorder({
  maxSeconds,
  onClip,
}: {
  maxSeconds: number;
  onClip: (clip: Blob) => void;
}) {
  const [supported, setSupported] = useState(false);
  const [state, setState] = useState<RecorderState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const frame = useRef<number | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAt = useRef(0);
  const discard = useRef(false);
  const onClipRef = useRef(onClip);

  useEffect(() => {
    onClipRef.current = onClip;
  }, [onClip]);

  useEffect(() => {
    // Feature detection must wait for the browser (not available during server render).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSupported(
      typeof window !== "undefined" &&
        typeof MediaRecorder !== "undefined" &&
        !!navigator.mediaDevices?.getUserMedia,
    );
  }, []);

  const release = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    if (frame.current) cancelAnimationFrame(frame.current);
    timer.current = null;
    frame.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    void audioContext.current?.close().catch(() => {});
    audioContext.current = null;
    setLevel(0);
  }, []);

  // Never leave the mic on if the component goes away mid-recording.
  useEffect(
    () => () => {
      discard.current = true;
      if (recorder.current?.state === "recording") recorder.current.stop();
      release();
    },
    [release],
  );

  const stop = useCallback(() => {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }, []);

  const cancel = useCallback(() => {
    discard.current = true;
    stop();
  }, [stop]);

  const watchLevel = useCallback((media: MediaStream) => {
    try {
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      ctx.createMediaStreamSource(media).connect(analyser);
      audioContext.current = ctx;
      void ctx.resume().catch(() => {});
      const samples = new Uint8Array(analyser.fftSize);
      let shown = 0;
      const tick = () => {
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (const s of samples) sum += ((s - 128) / 128) ** 2;
        const rms = Math.sqrt(sum / samples.length);
        const next = Math.min(1, rms * LEVEL_GAIN);
        // Re-render only on visible change.
        if (Math.abs(next - shown) > 0.04) {
          shown = next;
          setLevel(next);
        }
        frame.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // The meter is a nicety; recording works without it.
    }
  }, []);

  const start = useCallback(async () => {
    if (state !== "idle") return;
    setError(null);
    setState("starting");
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      setError(micErrorMessage(err));
      setState("idle");
      return;
    }
    const mimeType = pickMimeType();
    let rec: MediaRecorder;
    try {
      rec = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
    } catch {
      media.getTracks().forEach((t) => t.stop());
      setError("This browser can't record audio. You can type instead.");
      setState("idle");
      return;
    }

    const chunks: Blob[] = [];
    discard.current = false;
    stream.current = media;
    recorder.current = rec;
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      const elapsed = (Date.now() - startedAt.current) / 1000;
      release();
      setState("idle");
      if (discard.current) return;
      if (elapsed < MIN_SECONDS) {
        setError("That was very short. Tap the mic and talk for a few seconds.");
        return;
      }
      onClipRef.current(new Blob(chunks, { type: rec.mimeType || mimeType || "audio/webm" }));
    };

    rec.start();
    startedAt.current = Date.now();
    setSeconds(0);
    setState("recording");
    watchLevel(media);
    timer.current = setInterval(() => {
      const s = Math.floor((Date.now() - startedAt.current) / 1000);
      setSeconds(s);
      if (s >= maxSeconds) stop();
    }, 250);
  }, [state, maxSeconds, release, stop, watchLevel]);

  return { supported, state, seconds, level, error, start, stop, cancel, clearError: () => setError(null) };
}
