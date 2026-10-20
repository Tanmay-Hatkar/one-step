// Lays out the kitchen map: your dishes in the middle, each one's cousins around it.
// Pure and deterministic (same input → same picture), so it's easy to reason about.

import type { MapCousin, UserDish } from "./types";

export type NodeKind = "kitchen" | "cooked" | "one_step" | "far";

export interface MapNode {
  id: string;
  label: string;
  kind: NodeKind;
  x: number;
  y: number;
  /** Catalog id, for tapping a cousin. */
  dishId?: string;
}

export interface MapEdge {
  from: string;
  to: string;
  oneStep: boolean;
}

export const MAP_WIDTH = 360;
export const MAP_HEIGHT = 440;

const KITCHEN_RING = 58; // radius of the kitchen cluster when there are several dishes
const ONE_STEP_DISTANCE = 92; // from its anchor
const FAR_DISTANCE = 150;
const MARGIN_X = 44; // room for labels at the sides
const MARGIN_Y = 22;
const RELAX_ITERATIONS = 160;
// Nodes repel inside an ellipse wider than tall, because labels are wide.
const REPEL_X = 48;
const REPEL_Y = 30;
const MIN_WEDGE = 3;
const FIT_PADDING = 36; // around the drawing, for labels
const MIN_VIEW_WIDTH = 300; // never zoom in so far that labels get huge
const MAX_LABEL = 18;
const KITCHEN_LABEL = 24; // your own dishes get more room

export function shortLabel(name: string, max = MAX_LABEL): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function layoutMap(
  kitchen: UserDish[],
  cousins: MapCousin[],
): { nodes: MapNode[]; edges: MapEdge[]; viewBox: string } {
  const cx = MAP_WIDTH / 2;
  const cy = MAP_HEIGHT / 2;
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];

  const byAnchor = new Map<string, MapCousin[]>();
  for (const c of cousins) {
    const list = byAnchor.get(c.delta.anchor_name) ?? [];
    list.push(c);
    byAnchor.set(c.delta.anchor_name, list);
  }

  // Each kitchen dish gets a slice of the circle sized to how many cousins it has,
  // so a busy dish fans out and a quiet one doesn't waste space.
  // The +MIN_WEDGE floor keeps your dishes apart even when one has no cousins.
  const weights = kitchen.map((d) => (byAnchor.get(d.name)?.length ?? 0) + MIN_WEDGE);
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  const wedges = new Map<string, { mid: number; size: number }>();
  let start = -Math.PI / 2;
  kitchen.forEach((dish, i) => {
    const size = (2 * Math.PI * weights[i]) / totalWeight;
    const mid = kitchen.length === 1 ? -Math.PI / 2 : start + size / 2;
    start += size;
    wedges.set(dish.name, { mid, size });
    const r = kitchen.length === 1 ? 0 : KITCHEN_RING;
    nodes.push({
      id: kitchenId(dish.name),
      label: shortLabel(dish.name, KITCHEN_LABEL),
      kind: dish.source === "cooked" ? "cooked" : "kitchen",
      x: cx + r * Math.cos(mid),
      y: cy + r * Math.sin(mid),
    });
  });

  for (const [anchor, group] of byAnchor) {
    const anchorNode = nodes.find((n) => n.id === kitchenId(anchor));
    const wedge = wedges.get(anchor);
    if (!anchorNode || !wedge) continue;
    group.forEach((c, j) => {
      // Spread evenly across 90% of the wedge, centred on its middle.
      const t = (j + 0.5) / group.length - 0.5;
      const angle = wedge.mid + wedge.size * 0.9 * t;
      const r = c.delta.is_one_step ? ONE_STEP_DISTANCE : FAR_DISTANCE;
      nodes.push({
        id: c.dish.id,
        label: shortLabel(c.dish.name),
        kind: c.delta.is_one_step ? "one_step" : "far",
        x: anchorNode.x + r * Math.cos(angle),
        y: anchorNode.y + r * Math.sin(angle),
        dishId: c.dish.id,
      });
      edges.push({ from: anchorNode.id, to: c.dish.id, oneStep: c.delta.is_one_step });
    });
  }

  relax(nodes);
  return { nodes, edges, viewBox: fitViewBox(nodes) };
}

export function kitchenId(name: string): string {
  return `kitchen:${name}`;
}

/** Push overlapping nodes apart (kitchen nodes stay put), then keep everything in bounds. */
function relax(nodes: MapNode[]): void {
  const movable = (n: MapNode) => n.kind === "one_step" || n.kind === "far";
  for (let iter = 0; iter < RELAX_ITERATIONS; iter++) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        if (dx === 0 && dy === 0) {
          dx = 0.5 - ((i * 7 + j * 3) % 10) / 10; // deterministic nudge
          dy = 0.1;
        }
        const d = Math.hypot(dx / REPEL_X, dy / REPEL_Y);
        if (d >= 1) continue;
        // Unit direction in pixels; overlap depth scaled to pixels along that direction.
        const len = Math.hypot(dx, dy);
        const ux = dx / len;
        const uy = dy / len;
        const depth = (1 - d) * Math.hypot(ux * REPEL_X, uy * REPEL_Y);
        const moveA = movable(a);
        const moveB = movable(b);
        // Split the correction when both can move; otherwise the movable one takes it all.
        const step = (moveA && moveB ? 0.5 : 1) * depth * 0.5;
        if (moveA) {
          a.x -= ux * step;
          a.y -= uy * step;
        }
        if (moveB) {
          b.x += ux * step;
          b.y += uy * step;
        }
      }
    }
    for (const n of nodes) {
      if (!movable(n)) continue;
      n.x = Math.min(MAP_WIDTH - MARGIN_X, Math.max(MARGIN_X, n.x));
      n.y = Math.min(MAP_HEIGHT - MARGIN_Y, Math.max(MARGIN_Y, n.y));
    }
  }
}

/** A viewBox around the drawing (plus room for labels), so there's no empty canvas. */
function fitViewBox(nodes: MapNode[]): string {
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  let minX = Math.min(...xs) - FIT_PADDING * 1.6;
  let maxX = Math.max(...xs) + FIT_PADDING * 1.6;
  const minY = Math.min(...ys) - FIT_PADDING;
  const maxY = Math.max(...ys) + FIT_PADDING;
  if (maxX - minX < MIN_VIEW_WIDTH) {
    const grow = (MIN_VIEW_WIDTH - (maxX - minX)) / 2;
    minX -= grow;
    maxX += grow;
  }
  const r = (v: number) => Math.round(v * 10) / 10;
  return `${r(minX)} ${r(minY)} ${r(maxX - minX)} ${r(maxY - minY)}`;
}
