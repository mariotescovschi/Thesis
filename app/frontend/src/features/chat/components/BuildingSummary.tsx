import { Building2 } from 'lucide-react';
import { useProject } from '@/features/projects';
import { useOutputDocuments } from '@/features/viewer';

interface BuildingSummaryProps {
  projectId: string;
}

/** Aggregated, multi-floor overview: stacking order, per-floor room counts,
 *  total known area, and cross-floor links. Room data comes from each floor's
 *  full output Document (the manifest floors are light, with no polygons). */
export const BuildingSummary = ({ projectId }: BuildingSummaryProps) => {
  const { data: project } = useProject(projectId);
  const floors = project?.floors ?? [];
  const doneIds = floors.filter((f) => f.status === 'done').map((f) => f.id);
  const docs = useOutputDocuments(projectId, doneIds);

  if (!project || floors.length <= 1) return null;

  // floorId -> { rooms, area } from the fetched documents (keyed by doneIds order).
  const stats = new Map<string, { rooms: number; area: number }>();
  doneIds.forEach((id, i) => {
    const doc = docs[i]?.data;
    if (!doc) return;
    const rooms = doc.elements.filter((e) => e.kind === 'room');
    stats.set(id, {
      rooms: rooms.length,
      area: rooms.reduce((a, e) => a + (e.area_m2 ?? 0), 0),
    });
  });
  const totalArea = [...stats.values()].reduce((a, s) => a + s.area, 0);

  return (
    <section className="space-y-2 rounded-lg border border-border bg-card/40 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Building2 className="size-4 text-muted-foreground" />
        {project.name}
      </div>

      <ul className="space-y-1 text-xs">
        {floors.map((f, i) => {
          const s = stats.get(f.id);
          const label =
            f.status === 'done' ? `${s?.rooms ?? 0} rooms` : f.status;
          return (
            <li key={f.id} className="flex justify-between gap-2 text-muted-foreground">
              <span className="truncate">
                <span className="text-foreground">{i + 1}.</span> {f.name}
              </span>
              <span className="shrink-0">{label}</span>
            </li>
          );
        })}
      </ul>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Total area</span>
        <span>{totalArea > 0 ? `${totalArea.toFixed(2)} m²` : 'n/a'}</span>
      </div>

      <div className="text-xs">
        <p className="text-muted-foreground">Links ({project.links.length})</p>
        {project.links.length > 0 && (
          <ul className="mt-1 space-y-0.5">
            {project.links.map((l, i) => (
              <li key={i} className="text-foreground">
                {l.type}: {l.from_floor} ↔ {l.to_floor}
                {l.via ? ` (via ${l.via})` : ''}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
};
