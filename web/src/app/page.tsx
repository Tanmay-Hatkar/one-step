import { Kitchen } from "@/components/kitchen";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-10 pb-16 sm:pt-16">
      <Kitchen />
      <footer className="mt-16 text-xs text-muted-foreground">
        A side project by{" "}
        <a
          href="https://github.com/Tanmay-Hatkar/one-step"
          className="underline underline-offset-2 hover:text-foreground"
        >
          Tanmay Hatkar
        </a>
        . Diet filters check each dish&apos;s ingredients, but suggestions are AI-assisted — always
        check labels for allergies.
      </footer>
    </main>
  );
}
