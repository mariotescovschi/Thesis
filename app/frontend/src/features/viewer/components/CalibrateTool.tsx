import { useState } from 'react';
import { Ruler } from 'lucide-react';

interface CalibrateToolProps {
  pixelLength: number | null; // captured segment length; null = nothing drawn yet
  currentScale?: number | null;
  onConfirm: (meters: number) => void;
  onCancel: () => void;
}

/**
 * Calibration HUD shown while the `calibrate` tool is active. The user draws a
 * reference segment on the canvas; once captured, they enter its real length in
 * metres and we derive `scale_px_per_m = pixel_length / meters`.
 */
export const CalibrateTool = ({
  pixelLength,
  currentScale,
  onConfirm,
  onCancel,
}: CalibrateToolProps) => {
  const [meters, setMeters] = useState('');
  const value = parseFloat(meters);
  const valid = pixelLength != null && pixelLength > 0 && value > 0;

  return (
    <div className="w-72 rounded-lg border border-border bg-card/95 p-3 text-sm shadow-lg backdrop-blur">
      <div className="mb-2 flex items-center gap-2 text-foreground">
        <Ruler className="size-4" />
        <span className="font-medium">Calibrate scale</span>
      </div>

      <p className="mb-2 text-xs text-muted-foreground">
        Current: {currentScale ? `${currentScale.toFixed(1)} px/m` : 'not set'}
      </p>

      {pixelLength == null ? (
        <p className="text-xs text-muted-foreground">
          Click two points along a known distance (e.g. a wall you know the length of).
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            Segment length: <span className="text-foreground">{pixelLength.toFixed(1)} px</span>
          </p>
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted-foreground">Real length (metres)</span>
            <input
              autoFocus
              type="number"
              min="0"
              step="0.01"
              value={meters}
              onChange={(e) => setMeters(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && valid && onConfirm(value)}
              className="rounded-md border border-border bg-background px-2 py-1 text-foreground outline-none focus:border-primary"
              placeholder="e.g. 3.5"
            />
          </label>
          <div className="flex gap-2">
            <button
              disabled={!valid}
              onClick={() => onConfirm(value)}
              className="flex-1 rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              Apply scale
            </button>
            <button
              onClick={onCancel}
              className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
