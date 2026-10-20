"use client";

import { CheckCircle2, ChevronDown, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getEvals } from "@/lib/api";
import type { EvalCase, EvalResults, EvalSuite } from "@/lib/types";
import { cn } from "@/lib/utils";

const REPO_EVALS = "https://github.com/Tanmay-Hatkar/one-step/tree/main/api/evals";

/** What each suite measures, in plain words. Order is the order they're shown. */
const SUITES: { id: string; title: string; what: string; usesAI: boolean }[] = [
  {
    id: "parse",
    title: "Reading your cooking",
    what: "Does it turn “what I usually cook” into the right dish, protein, starch, techniques, equipment and key ingredients?",
    usesAI: true,
  },
  {
    id: "diff",
    title: "Writing the difference",
    what: "Is each write-up grounded? 2–5 short bullets, mentions the new ingredients, never adds your own ingredients to a dish that doesn't use them, no internal jargon.",
    usesAI: true,
  },
  {
    id: "e2e",
    title: "Finding relevant dishes",
    what: "From your words to suggestions: enough dishes, of the right kind, from several regions.",
    usesAI: true,
  },
  {
    id: "diet",
    title: "Diet safety",
    what: "Every diet rule (vegetarian and 9 allergens), swept over 152 kitchens across suggestions, tonight's picks and the map: no dish shown may break it, by its tags or by any ingredient.",
    usesAI: false,
  },
];

function percent(passed: number, total: number): string {
  return total ? `${Math.round((100 * passed) / total)}%` : "—";
}

export function EvalReport() {
  const [results, setResults] = useState<EvalResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvals()
      .then(setResults)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load results."));
  }, []);

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <Link href="/" className="text-sm font-medium tracking-wide text-primary">
          One Step
        </Link>
        <h1 className="font-heading text-4xl leading-[1.05] font-semibold tracking-tight">
          How well it works
        </h1>
        <p className="text-muted-foreground">
          One Step uses AI for language only — reading how you cook and writing what&apos;s
          different. Everything else, like ranking and diet rules, is plain code. These checks run
          automatically on every change, against the real model.
        </p>
      </header>

      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}
      {!results && !error && <Skeleton className="h-40 w-full rounded-2xl" />}

      {results && (
        <>
          <section aria-label="Summary" className="space-y-4">
            <div className="rounded-2xl border bg-card p-5">
              <p className="text-sm text-muted-foreground">Checks passing</p>
              <p className="font-heading text-6xl font-semibold tracking-tight">
                {percent(results.passed, results.total)}
              </p>
              <p className="text-sm text-muted-foreground">
                {results.passed} of {results.total} checks · model{" "}
                <code className="text-foreground">{results.model}</code> · run{" "}
                {new Date(results.run_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {SUITES.filter((s) => results.suites[s.id]).map((s) => {
                const suite = results.suites[s.id];
                return (
                  <a
                    key={s.id}
                    href={`#${s.id}`}
                    className="rounded-xl border bg-card p-4 hover:bg-muted/50"
                  >
                    <p className="text-xs text-muted-foreground">{s.title}</p>
                    <p className="font-heading text-3xl font-semibold">
                      {percent(suite.passed, suite.total)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {suite.passed}/{suite.total} checks
                    </p>
                  </a>
                );
              })}
            </div>
          </section>

          {SUITES.filter((s) => results.suites[s.id]).map((s) => (
            <SuiteSection key={s.id} meta={s} suite={results.suites[s.id]} />
          ))}

          <p className="text-sm text-muted-foreground">
            The test cases and checks are open source:{" "}
            <a href={REPO_EVALS} className="underline underline-offset-2 hover:text-foreground">
              api/evals
            </a>
            .
          </p>
        </>
      )}
    </div>
  );
}

function SuiteSection({ meta, suite }: { meta: (typeof SUITES)[number]; suite: EvalSuite }) {
  return (
    <section id={meta.id} aria-labelledby={`${meta.id}-title`} className="scroll-mt-6 space-y-3">
      <div>
        <h2 id={`${meta.id}-title`} className="font-heading text-2xl font-semibold tracking-tight">
          {meta.title}
        </h2>
        <p className="text-sm text-muted-foreground">
          {meta.what} {meta.usesAI ? "Uses the live model." : "Plain code — no AI involved."}
        </p>
      </div>
      <ul className="divide-y rounded-xl border bg-card">
        {suite.results.map((c) => (
          <CaseRow key={c.id} result={c} />
        ))}
      </ul>
    </section>
  );
}

function CaseRow({ result }: { result: EvalCase }) {
  const passed = result.checks.filter((c) => c.passed).length;
  const ok = passed === result.checks.length;
  return (
    <li>
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 text-sm">
          {ok ? (
            <CheckCircle2 aria-label="Passed" className="size-4 shrink-0 text-primary" />
          ) : (
            <XCircle aria-label="Failed" className="size-4 shrink-0 text-destructive" />
          )}
          <span className="flex-1 font-medium">{result.id.replaceAll("_", " ")}</span>
          <span className="text-muted-foreground tabular-nums">
            {passed}/{result.checks.length}
          </span>
          <ChevronDown
            aria-hidden
            className="size-4 text-muted-foreground transition-transform group-open:rotate-180"
          />
        </summary>
        <div className="space-y-3 px-4 pb-4 text-sm">
          {result.sample && (
            <div className="rounded-lg bg-muted p-3">
              <p className="font-medium">{result.sample.headline}</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {result.sample.changes.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          {result.cousins && (
            <p className="text-muted-foreground">Suggested: {result.cousins.join(", ")}</p>
          )}
          <table className="w-full text-left text-xs">
            <caption className="sr-only">Checks for {result.id}</caption>
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-1 pr-2 font-medium">Check</th>
                <th className="py-1 pr-2 font-medium">Result</th>
                <th className="py-1 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {result.checks.map((c) => (
                <tr key={c.name} className="border-t align-top">
                  <td className="py-1.5 pr-2 font-mono break-all">{c.name}</td>
                  <td className={cn("py-1.5 pr-2", c.passed ? "text-foreground" : "text-destructive")}>
                    {c.passed ? "pass" : "fail"}
                  </td>
                  <td className="py-1.5 break-words text-muted-foreground">{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </li>
  );
}
