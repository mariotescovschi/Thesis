// Pure snapping helpers for canvas geometry editing. State in → value out, no I/O.

export interface World {
  x: number;
  y: number;
}

export interface SnapOptions {
  step: number; // grid spacing in image px
  threshold: number; // vertex-snap radius in image px
}

export const snapToGrid = (v: number, step: number): number =>
  step > 0 ? Math.round(v / step) * step : Math.round(v);

/**
 * Snap a point to the nearest existing vertex within `threshold`, else to the grid.
 * `vertices` are raw `[x, y]` pairs (e.g. every polygon vertex on the floor).
 */
export const snapPoint = (
  p: World,
  vertices: number[][],
  { step, threshold }: SnapOptions,
): World => {
  let best: World | null = null;
  let bestDist = threshold;
  for (const [x, y] of vertices) {
    const d = Math.hypot(x - p.x, y - p.y);
    if (d < bestDist) {
      bestDist = d;
      best = { x, y };
    }
  }
  return best ?? { x: snapToGrid(p.x, step), y: snapToGrid(p.y, step) };
};
