"use client";

import { ArrowLeft, ArrowRight, Check, HelpCircle, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ToggleChip } from "@/components/toggle-chip";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getQuestions } from "@/lib/api";
import { repertoireOf } from "@/lib/kitchen";
import { equipmentLabel, techniqueLabel } from "@/lib/labels";
import { type Answers, applyAnswers } from "@/lib/patch";
import type { CookedDish } from "@/lib/storage";
import type { Diet, Have, Question, UserDish } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Shows what the app understood, before it searches: what you said (solid chips),
 * what it guessed (dashed, to keep or remove), and a few quick questions — only ones
 * whose answers would change your suggestions.
 */
export function ConfirmKitchen({
  dishes,
  cooked,
  diet,
  have,
  dismissed,
  error,
  onConfirm,
  onBack,
}: {
  dishes: UserDish[];
  cooked: CookedDish[];
  diet: Diet;
  have: Have;
  dismissed: string[];
  error: string | null;
  onConfirm: (dishes: UserDish[], have: Have, answered: string[]) => void;
  onBack: () => void;
}) {
  const [draft, setDraft] = useState(dishes);
  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [answers, setAnswers] = useState<Answers>({});

  // Ask once, for the kitchen as parsed; answers then apply locally and can be changed.
  useEffect(() => {
    let live = true;
    getQuestions(repertoireOf(dishes, cooked), diet, have, dismissed)
      .then((q) => live && setQuestions(q))
      .catch(() => live && setQuestions([])); // questions are optional; never block on them
    return () => {
      live = false;
    };
    // Only on entering this screen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const effective = useMemo(
    () => applyAnswers(draft, have, questions ?? [], answers),
    [draft, have, questions, answers],
  );

  function updateDish(index: number, next: UserDish) {
    setDraft((all) => all.map((d, i) => (i === index ? next : d)));
  }

  function choose(question: Question, index: number) {
    setAnswers((all) => {
      const current = all[question.id] ?? [];
      const none = question.options[index].label === "None of these";
      if (!question.multi) return { ...all, [question.id]: current[0] === index ? [] : [index] };
      if (none) return { ...all, [question.id]: [index] };
      const noneIndex = question.options.findIndex((o) => o.label === "None of these");
      const picked = current.includes(index)
        ? current.filter((i) => i !== index)
        : [...current.filter((i) => i !== noneIndex), index];
      return { ...all, [question.id]: picked };
    });
  }

  const answered = Object.entries(answers)
    .filter(([, picked]) => picked.length)
    .map(([id]) => id);

  return (
    <section aria-labelledby="heard" className="space-y-6">
      <div className="space-y-1">
        <p className="text-sm font-medium tracking-wide text-primary">One Step</p>
        <h1 id="heard" className="font-heading text-3xl font-semibold tracking-tight">
          Here&apos;s what I heard
        </h1>
        <p className="text-[15px] text-muted-foreground">
          Fix anything that&apos;s off. Dashed ones are my guesses — tap to keep, × to remove.
        </p>
      </div>

      <div className="space-y-3">
        {draft.map((dish, i) =>
          isPicked(dish) ? null : (
            <DishCheck
              key={`${dish.name}-${i}`}
              dish={dish}
              shown={effective.dishes[i] ?? dish}
              onChange={(next) => updateDish(i, next)}
            />
          ),
        )}
        {draft.some(isPicked) && (
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Also in your kitchen: </span>
            {draft
              .filter(isPicked)
              .map((d) => d.name)
              .join(", ")}
          </p>
        )}
      </div>

      {questions === null ? (
        <div className="space-y-2" aria-label="Loading questions">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      ) : (
        questions.length > 0 && (
          <div className="space-y-3">
            <h2 className="font-heading text-xl font-semibold tracking-tight">
              {questions.length === 1 ? "One quick question" : "A few quick questions"}
            </h2>
            {questions.map((q) => (
              <QuestionCard
                key={q.id}
                question={q}
                picked={answers[q.id] ?? []}
                onPick={(index) => choose(q, index)}
              />
            ))}
            <p className="text-xs text-muted-foreground">
              Optional. I only ask when the answer changes what I&apos;d suggest.
            </p>
          </div>
        )
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          size="lg"
          onClick={() => onConfirm(effective.dishes, effective.have, answered)}
          className="h-11 text-base sm:px-5"
        >
          Looks right — show me dishes
          <ArrowRight aria-hidden />
        </Button>
        <Button variant="ghost" size="lg" onClick={onBack} className="h-11">
          <ArrowLeft aria-hidden />
          Change what I said
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </section>
  );
}

/** A tapped photo tile: a catalog dish as-is, so there's nothing to check. */
function isPicked(dish: UserDish): boolean {
  return Boolean(dish.matched_dish_id) && !dish.notes && dish.source !== "cooked";
}

function DishCheck({
  dish,
  shown,
  onChange,
}: {
  dish: UserDish;
  /** The dish with answers applied — what will actually be used. */
  shown: UserDish;
  onChange: (next: UserDish) => void;
}) {
  const guesses = dish.assumed_ingredients ?? [];
  const removeSaid = (item: string) =>
    onChange({ ...dish, key_ingredients: dish.key_ingredients.filter((i) => i !== item) });
  const keepGuess = (item: string) =>
    onChange({
      ...dish,
      key_ingredients: [...dish.key_ingredients, item],
      assumed_ingredients: guesses.filter((i) => i !== item),
    });
  const dropGuess = (item: string) =>
    onChange({ ...dish, assumed_ingredients: guesses.filter((i) => i !== item) });

  return (
    <Card className="gap-3 px-4 py-4">
      <div>
        <h3 className="font-heading text-xl leading-tight font-semibold tracking-tight">
          {dish.name}
        </h3>
        {dish.notes && (
          <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">{dish.notes}</p>
        )}
      </div>

      <ul className="flex flex-wrap gap-1.5" aria-label={`Ingredients in ${dish.name}`}>
        {dish.key_ingredients.map((item) => (
          <li
            key={item}
            className="inline-flex h-7 items-center gap-0.5 rounded-full border bg-background pr-1 pl-2.5 text-sm"
          >
            {item}
            <button
              type="button"
              onClick={() => removeSaid(item)}
              disabled={dish.key_ingredients.length <= 1}
              aria-label={`Remove ${item}`}
              className="grid size-5 place-items-center rounded-full text-muted-foreground hover:bg-muted disabled:opacity-30"
            >
              <X aria-hidden className="size-3" />
            </button>
          </li>
        ))}
        {guesses.map((item) => (
          <li
            key={`guess-${item}`}
            className="inline-flex h-7 items-center rounded-full border border-dashed border-primary/50 text-sm text-muted-foreground"
          >
            <button
              type="button"
              onClick={() => keepGuess(item)}
              aria-label={`Keep ${item} — I use it`}
              className="inline-flex h-full items-center gap-1 rounded-l-full pr-1 pl-2.5 hover:bg-primary/10 hover:text-foreground"
            >
              <HelpCircle aria-hidden className="size-3.5 text-primary" />
              {item}
            </button>
            <button
              type="button"
              onClick={() => dropGuess(item)}
              aria-label={`Remove ${item} — I don't use it`}
              className="grid h-full w-6 place-items-center rounded-r-full hover:bg-muted"
            >
              <X aria-hidden className="size-3" />
            </button>
          </li>
        ))}
      </ul>

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">How</dt>
        <dd>{shown.techniques.map(techniqueLabel).join(" · ")}</dd>
        <dt className="text-muted-foreground">With</dt>
        <dd>{shown.equipment.map(equipmentLabel).join(" · ")}</dd>
      </dl>
    </Card>
  );
}

function QuestionCard({
  question,
  picked,
  onPick,
}: {
  question: Question;
  picked: number[];
  onPick: (index: number) => void;
}) {
  const id = `q-${question.id}`;
  return (
    <Card className="gap-2.5 px-4 py-4">
      {question.about && (
        <p className="text-xs font-semibold tracking-wide text-primary uppercase">
          {question.about}
        </p>
      )}
      <p id={id} className="text-[15px] font-medium">
        {question.text}
        {question.multi && (
          <span className="font-normal text-muted-foreground"> Pick any.</span>
        )}
      </p>
      <div role="group" aria-labelledby={id} className="flex flex-wrap gap-2">
        {question.options.map((option, index) => (
          <ToggleChip
            key={option.label}
            pressed={picked.includes(index)}
            onClick={() => onPick(index)}
          >
            {picked.includes(index) && <Check aria-hidden className="size-3.5" />}
            {option.label}
          </ToggleChip>
        ))}
      </div>
      <p className={cn("text-xs text-muted-foreground")}>{question.why}</p>
    </Card>
  );
}
