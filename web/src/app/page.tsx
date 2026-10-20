import { Kitchen } from "@/components/kitchen";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-10 pb-16 sm:pt-16">
      <header className="mb-8 space-y-3">
        <p className="text-sm font-medium tracking-wide text-primary">One Step</p>
        <h1 className="font-heading text-4xl leading-[1.05] font-semibold tracking-tight sm:text-5xl">
          You can already cook dishes you&apos;ve never heard of.
        </h1>
        <p className="text-base text-muted-foreground">
          Tell me what you usually make. I&apos;ll show you dishes from around the world that are
          one step away — written as only what&apos;s different from your version.
        </p>
      </header>
      <Kitchen />
      <footer className="mt-16 text-xs text-muted-foreground">
        A side project by{" "}
        <a
          href="https://github.com/Tanmay-Hatkar/one-step"
          className="underline underline-offset-2 hover:text-foreground"
        >
          Tanmay Hatkar
        </a>
        . Suggestions are AI-assisted — check allergens yourself.
      </footer>
    </main>
  );
}
