import { Fragment } from 'react';
import { Line } from 'react-konva';

const PIXEL_STEP = 50; // default grid spacing in image px when no scale is known
const STROKE = '#ffffff';

interface GridOverlayProps {
  width: number;
  height: number;
  scalePxPerM?: number | null; // when set, grid spacing = 1 metre
}

/**
 * Non-interactive reference grid. Spacing is 1 metre when `scalePxPerM` is known
 * (metric), otherwise a fixed pixel step. Step is clamped so a tiny/huge scale never
 * produces thousands of lines. Lines stay 1px on screen (strokeScaleEnabled=false).
 */
export const GridOverlay = ({ width, height, scalePxPerM }: GridOverlayProps) => {
  let step = scalePxPerM && scalePxPerM > 0 ? scalePxPerM : PIXEL_STEP;
  const span = Math.max(width, height);
  while (step > 0 && span / step > 400) step *= 2; // cap line count
  if (step < 4) step = PIXEL_STEP;

  const lines = [];
  for (let x = 0; x <= width; x += step) {
    lines.push(
      <Line
        key={`v${x}`}
        points={[x, 0, x, height]}
        stroke={STROKE}
        strokeWidth={0.5}
        opacity={0.08}
        strokeScaleEnabled={false}
      />,
    );
  }
  for (let y = 0; y <= height; y += step) {
    lines.push(
      <Line
        key={`h${y}`}
        points={[0, y, width, y]}
        stroke={STROKE}
        strokeWidth={0.5}
        opacity={0.08}
        strokeScaleEnabled={false}
      />,
    );
  }
  return <Fragment>{lines}</Fragment>;
};
