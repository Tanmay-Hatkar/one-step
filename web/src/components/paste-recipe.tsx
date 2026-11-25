"use client";

import { ClipboardPaste, ExternalLink, ImageUp, Loader2, TriangleAlert, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { CousinCard } from "@/components/cousin-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, pastePhoto, pasteRecipe } from "@/lib/api";
import { ALLERGENS } from "@/lib/labels";
import { MAX_PASTE_CHARS, addPasted, removePasted, takeShared, usePasted } from "@/lib/pasted";
import type { Diet, Dish, Have, Pasted, UserDish } from "@/lib/types";

const MIN_CHARS = 8;
/** Photos are shrunk in the browser to this longest side before upload: plenty to read text. */
const PHOTO_MAX_SIDE = 1600;
const PHOTO_QUALITY = 0.85;

/** A phone photo can be 10 MB; a JPEG this size reads just as well and uploads fast. */
async function shrink(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, PHOTO_MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((done) =>
      canvas.toBlob(done, "image/jpeg", PHOTO_QUALITY),
    );
    return blob ?? file;
  } catch {
    return file; // can't decode here: let the server decide
  }
}

/** "This has dairy and isn't vegetarian." — from the rules the API says it breaks. */
function dietWarning(broken: string[]): string {
  const labels = ALLERGENS.filter((a) => broken.includes(a.id)).map((a) => a.label.toLowerCase());
  const parts = [
    labels.length ? `has ${labels.join(", ")}` : "",
    broken.includes("vegetarian") ? "isn't vegetarian" : "",
  ].filter(Boolean);
  return `Heads up: this ${parts.join(" and ")}. You told me to avoid that.`;
}

/** Where a pasted link came from, short enough for a caption. */
function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "the source";
  }
}

/**
 * Bring a recipe from anywhere (a link, a caption, a message) and see it as changes to
 * something you already cook. Results stay on this device.
 */
export function PasteRecipe({
  repertoire,
  diet,
  have,
  isCooked,
  onCooked,
}: {
  repertoire: UserDish[];
  diet: Diet;
  have: Have;
  isCooked: (id: string) => boolean;
  onCooked: (dish: Dish) => void;
}) {
  const pasted = usePasted();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newest, setNewest] = useState<string | null>(null);
  const section = useRef<HTMLElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  // The kitchen can change while the box is open; always send the latest.
  const latest = useRef({ repertoire, diet, have });
  useEffect(() => {
    latest.current = { repertoire, diet, have };
  });

  /** Read a recipe (text, link or photo) and keep the result. */
  async function read(
    ask: (mine: UserDish[], rules: Diet, extra: Have) => Promise<Pasted>,
    fromPhoto = false,
  ) {
    setBusy(true);
    setError(null);
    try {
      const { repertoire: mine, diet: rules, have: extra } = latest.current;
      const result = await ask(mine, rules, extra);
      addPasted(result, fromPhoto);
      setNewest(result.cousin.dish.id);
      setText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function run(input: string) {
    const value = input.trim();
    if (value.length < MIN_CHARS) {
      setError("Paste a link to a recipe, or the recipe itself.");
      return;
    }
    await read((mine, rules, extra) => pasteRecipe(value, mine, rules, extra));
  }

  async function runPhoto(file: File | undefined) {
    if (!file) return;
    const photo = await shrink(file);
    await read((mine, rules, extra) => pastePhoto(photo, mine, rules, extra), true);
  }

  useEffect(() => {
    // Something shared to the app from another app: show it and read it straight away.
    const shared = takeShared();
    if (!shared) return;
    /* eslint-disable-next-line react-hooks/set-state-in-effect */
    setText(shared);
    void run(shared);
    // Runs once, when the paste box first appears.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section ref={section} aria-labelledby="paste" className="scroll-mt-4 space-y-3">
      <div className="space-y-4">
        <div className="space-y-1">
          <h1 id="paste" className="font-heading text-4xl leading-tight font-semibold tracking-tight">
            Bring a recipe
          </h1>
          <p className="text-[15px] text-muted-foreground">
            From a website, a video, a friend. I&apos;ll rewrite it as changes to a dish you
            already cook.
          </p>
        </div>
        <Textarea
          aria-label="A recipe link or the recipe text"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, MAX_PASTE_CHARS))}
          placeholder="Paste a link, a video caption, or the whole recipe"
          className="min-h-24 bg-card text-base"
          disabled={busy}
        />
        <div className="grid gap-2 sm:grid-cols-2">
          <Button onClick={() => run(text)} disabled={busy} className="h-11">
            {busy ? <Loader2 aria-hidden className="animate-spin" /> : <ClipboardPaste aria-hidden />}
            {busy ? "Reading it…" : "Show what's different"}
          </Button>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => fileInput.current?.click()}
            className="h-11"
          >
            <ImageUp aria-hidden />
            Use a screenshot or photo
          </Button>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          tabIndex={-1}
          aria-label="A screenshot or photo of a recipe"
          onChange={(e) => {
            void runPhoto(e.target.files?.[0]);
            e.target.value = ""; // picking the same picture again still fires
          }}
        />
        <p className="text-xs text-muted-foreground">
          Video recipe? Screenshot the caption or the ingredients on screen.
        </p>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>

      {busy && (
        <div className="space-y-3 rounded-xl border bg-card p-4" role="status" aria-live="polite">
          <p className="animate-pulse text-sm text-muted-foreground">
            Comparing it with your kitchen…
          </p>
          <Skeleton className="h-7 w-2/3" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
      )}

      {pasted.length > 0 && (
        <h2 className="pt-3 font-heading text-xl font-semibold tracking-tight">
          Recipes you brought
        </h2>
      )}
      {pasted.map((entry, i) => {
        const { dish } = entry.cousin;
        return (
          <div key={dish.id} className="space-y-1.5">
            {entry.breaks_diet.length > 0 && (
              <p className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
                <span>{dietWarning(entry.breaks_diet)}</span>
              </p>
            )}
            <CousinCard
              cousin={entry.cousin}
              index={i}
              label="You brought this"
              defaultOpen={dish.id === newest}
              cooked={isCooked(dish.id)}
              onCooked={() => onCooked(dish)}
            />
            <div className="flex items-center justify-between gap-3 px-1 text-xs text-muted-foreground">
              {entry.recipe.source_url ? (
                <a
                  href={entry.recipe.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-w-0 items-center gap-1 underline-offset-2 hover:underline"
                >
                  <ExternalLink aria-hidden className="size-3 shrink-0" />
                  <span className="truncate">From {hostOf(entry.recipe.source_url)}</span>
                </a>
              ) : (
                <span>{entry.fromPhoto ? "From your picture" : "From what you pasted"}</span>
              )}
              <button
                type="button"
                onClick={() => removePasted(dish.id)}
                className="inline-flex shrink-0 items-center gap-1 hover:text-foreground"
              >
                <X aria-hidden className="size-3" />
                Remove
              </button>
            </div>
          </div>
        );
      })}
    </section>
  );
}
