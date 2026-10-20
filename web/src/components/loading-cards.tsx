import { Skeleton } from "@/components/ui/skeleton";

export function LoadingCards({ label }: { label: string }) {
  return (
    <div className="space-y-4" role="status" aria-live="polite">
      <p className="animate-pulse text-sm text-muted-foreground">{label}</p>
      {[0, 1, 2].map((i) => (
        <div key={i} className="space-y-3 rounded-xl border bg-card p-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-2/3" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-4/6" />
        </div>
      ))}
    </div>
  );
}
