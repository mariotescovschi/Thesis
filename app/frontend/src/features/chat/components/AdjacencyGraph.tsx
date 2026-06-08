import type { Adjacency } from '@/features/projects';

interface AdjacencyGraphProps {
  adjacency: Adjacency[];
  roomNames: string[];
}

/** Simple circular-layout SVG graph of room adjacencies. */
export const AdjacencyGraph = ({ adjacency, roomNames }: AdjacencyGraphProps) => {
  const n = roomNames.length;
  if (n === 0) return null;

  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;

  const positions = roomNames.map((_, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  const nameIdx = new Map(roomNames.map((name, i) => [name, i]));

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="h-64 w-full">
      {/* Edges */}
      {adjacency.map((a, i) => {
        const fi = nameIdx.get(a.from);
        const ti = nameIdx.get(a.to);
        if (fi == null || ti == null) return null;
        return (
          <line
            key={i}
            x1={positions[fi].x}
            y1={positions[fi].y}
            x2={positions[ti].x}
            y2={positions[ti].y}
            className="stroke-muted-foreground/50"
            strokeWidth={1}
          />
        );
      })}
      {/* Nodes */}
      {roomNames.map((name, i) => (
        <g key={name}>
          <circle
            cx={positions[i].x}
            cy={positions[i].y}
            r={6}
            className="fill-primary/80 stroke-primary"
            strokeWidth={1}
          />
          <text
            x={positions[i].x}
            y={positions[i].y + 14}
            textAnchor="middle"
            className="fill-foreground text-[6px] capitalize"
          >
            {name.length > 10 ? name.slice(0, 9) + '…' : name}
          </text>
        </g>
      ))}
    </svg>
  );
};
