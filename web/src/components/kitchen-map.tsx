"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DishSheet } from "@/components/dish-sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getCousin, getMap } from "@/lib/api";
import { type MapNode, layoutMap } from "@/lib/map-layout";
import type { Cousin, Diet, Dish, KitchenMap as MapData, UserDish } from "@/lib/types";
import { cn } from "@/lib/utils";

const NODE_RADIUS: Record<MapNode["kind"], number> = {
  kitchen: 11,
  cooked: 9,
  one_step: 7,
  far: 6,
};
const HIT_RADIUS = 20; // tap target, bigger than the mark

/**
 * Your dishes in the middle, the dishes one step from them around them.
 * Tap a dish to see it written as a diff from your kitchen.
 */
export function KitchenMap({
  repertoire,
  diet,
  isCooked,
  onCooked,
  whose = "your",
}: {
  repertoire: UserDish[];
  /** "their" on someone else's shared kitchen. */
  whose?: "your" | "their";
  diet: Diet;
  isCooked: (id: string) => boolean;
  /** Omit for a read-only map (a shared kitchen). */
  onCooked?: (dish: Dish) => void;
}) {
  const [data, setData] = useState<MapData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [cousin, setCousin] = useState<Cousin | null>(null);
  const [sheetLoading, setSheetLoading] = useState(false);
  const [sheetError, setSheetError] = useState<string | null>(null);

  const key = JSON.stringify([repertoire.map((d) => d.name), diet]);
  useEffect(() => {
    let live = true;
    getMap(repertoire, diet)
      .then((m) => live && (setData(m), setError(null)))
      .catch((err) => live && setError(err instanceof ApiError ? err.message : "Couldn't draw the map."));
    return () => {
      live = false;
    };
    // `key` captures the inputs that matter; the arrays are rebuilt every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const layout = useMemo(() => (data ? layoutMap(data.kitchen, data.cousins) : null), [data]);
  const position = useMemo(
    () => new Map(layout?.nodes.map((n) => [n.id, n]) ?? []),
    [layout],
  );

  const open = useCallback(
    (dishId: string) => {
      setSelected(dishId);
      setCousin(null);
      setSheetError(null);
      setSheetLoading(true);
      getCousin(repertoire, dishId, diet)
        .then(setCousin)
        .catch((err) =>
          setSheetError(err instanceof ApiError ? err.message : "Couldn't load that dish."),
        )
        .finally(() => setSheetLoading(false));
    },
    [repertoire, diet],
  );
  const close = useCallback(() => setSelected(null), []);

  if (error) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {error}
      </p>
    );
  }
  if (!data || !layout) {
    return <Skeleton className="aspect-[36/44] w-full rounded-2xl" />;
  }

  return (
    <section aria-labelledby="map-title" className="space-y-3">
      <div>
        <h2 id="map-title" className="font-heading text-2xl font-semibold tracking-tight">
          {whose === "your" ? "Your map" : "Their map"}
        </h2>
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{data.one_step_count}</span> of{" "}
          {data.catalog_size} dishes are one step from {whose} kitchen.
          {whose === "your" && " Cook one and it grows new branches."}
        </p>
      </div>

      <div className="rounded-2xl border bg-card p-1">
        <svg
          viewBox={layout.viewBox}
          className="h-auto w-full touch-manipulation select-none"
          role="img"
          aria-label={`Map of ${data.kitchen.length} of your dishes and ${data.cousins.length} dishes near them`}
        >
          {layout.edges.map((e) => {
            const a = position.get(e.from);
            const b = position.get(e.to);
            if (!a || !b) return null;
            return (
              <line
                key={`${e.from}-${e.to}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                className={e.oneStep ? "stroke-primary/45" : "stroke-map-far/45"}
                strokeWidth={e.oneStep ? 2 : 1.5}
                strokeDasharray={e.oneStep ? undefined : "4 4"}
              />
            );
          })}
          {layout.nodes.map((n) => (
            <MapDot
              key={n.id}
              node={n}
              cooked={n.dishId ? isCooked(n.dishId) : false}
              selected={selected === n.dishId}
              onOpen={n.dishId ? () => open(n.dishId!) : undefined}
            />
          ))}
        </svg>
      </div>

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Legend">
        <li className="flex items-center gap-1.5">
          <svg width="14" height="14" aria-hidden>
            <circle cx="7" cy="7" r="6" className="fill-primary" />
          </svg>
          {whose === "your" ? "Your dishes" : "Their dishes"}
        </li>
        <li className="flex items-center gap-1.5">
          <svg width="14" height="14" aria-hidden>
            <circle cx="7" cy="7" r="5" className="fill-card stroke-primary" strokeWidth={2} />
          </svg>
          One step away
        </li>
        <li className="flex items-center gap-1.5">
          <svg width="14" height="14" aria-hidden>
            <circle
              cx="7"
              cy="7"
              r="5"
              className="fill-card stroke-map-far"
              strokeWidth={1.5}
              strokeDasharray="2 2"
            />
          </svg>
          Bigger step
        </li>
      </ul>
      <p className="text-xs text-muted-foreground">
        Tap any dish to see how it differs from {whose === "your" ? "yours" : "theirs"}.
      </p>

      {/* The same dishes as a list, for screen readers and anyone who prefers text. */}
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">Show as a list</summary>
        <ul className="mt-2 space-y-1">
          {data.cousins.map((c) => (
            <li key={c.dish.id}>
              <button
                type="button"
                onClick={() => open(c.dish.id)}
                className="text-left underline-offset-2 hover:underline"
              >
                {c.dish.name}
              </button>{" "}
              <span className="text-muted-foreground">
                — from {c.delta.anchor_name.toLowerCase()},{" "}
                {c.delta.is_one_step ? "one step" : "a bigger step"}
              </span>
            </li>
          ))}
        </ul>
      </details>

      {selected && (
        <DishSheet
          cousin={cousin}
          loading={sheetLoading}
          error={sheetError}
          cooked={isCooked(selected)}
          onCooked={
            onCooked && cousin
              ? () => {
                  onCooked(cousin.dish);
                  close();
                }
              : undefined
          }
          onClose={close}
        />
      )}
    </section>
  );
}

function MapDot({
  node,
  cooked,
  selected,
  onOpen,
}: {
  node: MapNode;
  cooked: boolean;
  selected: boolean;
  onOpen?: () => void;
}) {
  const r = NODE_RADIUS[node.kind];
  const mine = node.kind === "kitchen" || node.kind === "cooked";
  const dot = (
    <>
      {selected && <circle cx={node.x} cy={node.y} r={r + 5} className="fill-primary/20" />}
      <circle
        cx={node.x}
        cy={node.y}
        r={r}
        className={cn(
          // A 2px surface ring keeps dots legible where they cross lines.
          "stroke-card",
          mine && "fill-primary",
          node.kind === "cooked" && "fill-primary/70",
          node.kind === "one_step" && "fill-card stroke-primary",
          node.kind === "far" && "fill-card stroke-map-far",
          cooked && "fill-primary",
        )}
        strokeWidth={2}
        strokeDasharray={node.kind === "far" && !cooked ? "2 2" : undefined}
      />
      <text
        x={node.x}
        y={node.y + r + 12}
        textAnchor="middle"
        className={cn(
          "fill-foreground text-[11px]",
          mine ? "font-semibold" : "fill-muted-foreground",
          node.kind === "one_step" && "fill-foreground",
        )}
        style={{ paintOrder: "stroke" }}
        stroke="var(--card)"
        strokeWidth={3}
      >
        {node.label}
      </text>
    </>
  );

  if (!onOpen) return <g>{dot}</g>;
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={`${node.label}: ${node.kind === "one_step" ? "one step away" : "a bigger step"}`}
      onClick={onOpen}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen())}
      className="cursor-pointer outline-none [&:focus-visible>circle:first-child]:stroke-ring"
    >
      <circle cx={node.x} cy={node.y} r={HIT_RADIUS} className="fill-transparent" />
      {dot}
    </g>
  );
}
