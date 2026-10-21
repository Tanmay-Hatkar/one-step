import { InstallApp } from "@/components/install-app";
import { Kitchen } from "@/components/kitchen";

const CASE_STUDY =
  "https://github.com/Tanmay-Hatkar/one-step/blob/main/docs/case-study.md";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-10 pb-16 sm:pt-16">
      <Kitchen />
      <footer className="mt-16 text-xs text-muted-foreground">
        <InstallApp />A side project by{" "}
        <a
          href="https://github.com/Tanmay-Hatkar/one-step"
          className="underline underline-offset-2 hover:text-foreground"
        >
          Tanmay Hatkar
        </a>
        .{" "}
        <a
          href="/evals"
          className="underline underline-offset-2 hover:text-foreground"
        >
          How well it works
        </a>
        .{" "}
        <a
          href={CASE_STUDY}
          className="underline underline-offset-2 hover:text-foreground"
        >
          How it&apos;s built
        </a>
        . Diet filters check each dish&apos;s ingredients, but suggestions are
        AI-assisted — always check labels for allergies.
      </footer>
    </main>
  );
}
