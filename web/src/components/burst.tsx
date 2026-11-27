/** A short burst of dots around an icon, for cooking something new. CSS-only. */
const DOTS = 10;
const COLORS = ["var(--primary)", "oklch(0.8 0.15 85)", "oklch(0.7 0.14 150)"];

export function Burst() {
  return (
    <span aria-hidden className="pointer-events-none absolute inset-0">
      {Array.from({ length: DOTS }, (_, i) => (
        <span
          key={i}
          className="burst-dot absolute top-1/2 left-1/2 -mt-[3px] -ml-[3px] size-1.5 rounded-full"
          style={
            {
              "--angle": `${(360 / DOTS) * i}deg`,
              background: COLORS[i % COLORS.length],
              animation: "burst 700ms cubic-bezier(0.2, 0.7, 0.3, 1) forwards",
              animationDelay: `${(i % 3) * 30}ms`,
            } as React.CSSProperties
          }
        />
      ))}
    </span>
  );
}
