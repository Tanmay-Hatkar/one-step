export function Hero() {
  return (
    <header className="mb-8 space-y-4">
      <p className="flex items-center gap-2 text-sm font-medium tracking-wide text-primary">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/icon.svg" alt="" width={22} height={22} className="rounded-md" />
        One Step
      </p>
      <h1 className="font-heading text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-5xl">
        You can already cook dishes you&apos;ve never heard of.
      </h1>
      <p className="text-base text-muted-foreground">
        Tell me what you cook. I&apos;ll show you dishes from around the world that are one
        small change away, written as just the change.
      </p>
    </header>
  );
}
