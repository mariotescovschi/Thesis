import type { Element } from '@/features/projects';

// Shoelace polygon area in px² (pure).
const polygonAreaPx = (poly: number[][]): number => {
  let a = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    a += x1 * y2 - x2 * y1;
  }
  return Math.abs(a) / 2;
};

interface RoomRowProps {
  room: Element;
  scaleKnown: boolean;
  planAreaPx: number;
}

/** Read-only room row: type + area (m² when scale known, otherwise % of plan). */
export const RoomRow = ({ room, scaleKnown, planAreaPx }: RoomRowProps) => {
  const pct = planAreaPx > 0 ? (polygonAreaPx(room.polygon) / planAreaPx) * 100 : 0;
  const area = room.area_m2 != null ? Number(room.area_m2.toFixed(2)) : null;

  return (
    <li className="flex items-center justify-between gap-2 py-1">
      <span className="capitalize text-foreground">{room.type || room.label || room.id}</span>
      {scaleKnown && area != null ? (
        <span className="shrink-0 text-xs text-muted-foreground">{area} m²</span>
      ) : (
        <span className="shrink-0 text-xs text-muted-foreground" title="share of total plan area">
          ~{pct.toFixed(1)}%
        </span>
      )}
    </li>
  );
};
