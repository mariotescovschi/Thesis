import { useCallback, useMemo, useState } from 'react';
import type { Floor } from '@/features/projects';
import type { EditCommand } from '../types/command';
import type { EditorTool } from '../store/editorStore';
import { snapPoint, type World } from '../services/snap';

const SNAP: { step: number; threshold: number } = { step: 10, threshold: 8 };
const DRAW_TOOLS: EditorTool[] = ['wall', 'split', 'calibrate'];

export interface Calibration {
  a: World;
  b: World;
  pixelLength: number;
}

/**
 * Encapsulates the transient drawing interactions for the geometry tools.
 *
 * - `wall` / `split` / `calibrate` are two-click gestures (click start, click end) so
 *   they coexist with stage panning (a drag, not a click). A rubber-band preview
 *   follows the cursor between the two clicks.
 * - `calibrate` does not dispatch immediately: it captures the drawn segment so the
 *   caller can ask for the real-world length, then emit `set_scale`.
 * - `move` / `vertex` are handled by the draggable element itself, not here.
 *
 * The pending start point is tagged with the tool it was placed in, so a tool switch
 * invalidates it without an effect-driven reset (avoids setState-in-effect).
 */
export const useCanvasEditing = (
  tool: EditorTool,
  selection: string | null,
  doc: Floor | null,
  onApply: (command: EditCommand) => void,
) => {
  const [pending, setPending] = useState<(World & { tool: EditorTool }) | null>(null);
  const [cursor, setCursor] = useState<World | null>(null);
  const [calibration, setCalibration] = useState<Calibration | null>(null);

  const vertices = useMemo(
    () => (doc ? doc.elements.flatMap((el) => el.polygon) : []),
    [doc],
  );
  const snap = useCallback((p: World) => snapPoint(p, vertices, SNAP), [vertices]);

  const active = pending && pending.tool === tool ? pending : null;

  const onCanvasMouseMove = useCallback(
    (world: World) => {
      if (DRAW_TOOLS.includes(tool)) setCursor(snap(world));
    },
    [tool, snap],
  );

  const onCanvasClick = useCallback(
    (world: World) => {
      if (!DRAW_TOOLS.includes(tool)) return;
      const p = snap(world);
      if (tool === 'split' && !selection) return; // split needs a target room
      const start = pending && pending.tool === tool ? pending : null;
      if (!start) {
        if (tool === 'calibrate') setCalibration(null); // fresh measurement
        setPending({ ...p, tool });
        return;
      }
      if (tool === 'calibrate') {
        const pixelLength = Math.hypot(p.x - start.x, p.y - start.y);
        setCalibration({ a: { x: start.x, y: start.y }, b: p, pixelLength });
      } else {
        const segment = [
          [start.x, start.y],
          [p.x, p.y],
        ];
        if (tool === 'wall') onApply({ op: 'add_wall', segment });
        else onApply({ op: 'split_room', element_id: selection as string, segment });
      }
      setPending(null);
      setCursor(null);
    },
    [tool, selection, pending, snap, onApply],
  );

  const previewPoints =
    active && cursor ? [active.x, active.y, cursor.x, cursor.y] : null;
  const pendingPoint: World | null = active ? { x: active.x, y: active.y } : null;
  const clearCalibration = useCallback(() => setCalibration(null), []);

  return {
    onCanvasClick,
    onCanvasMouseMove,
    pending: pendingPoint,
    previewPoints,
    calibration,
    clearCalibration,
  };
};
