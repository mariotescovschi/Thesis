import { type ReactNode } from 'react';
import { useOutputDocument, useApplyEdit } from '@/features/viewer';
import { PricePanel } from '@/features/pricing';
import { AdjacencyEditor } from './AdjacencyEditor';
import { AdjacencyGraph } from './AdjacencyGraph';
import { RoomRow } from './RoomRow';
import { BuildingSummary } from './BuildingSummary';

const Section = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="space-y-1">
    <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      {title}
    </h3>
    {children}
  </section>
);

const Row = ({ label, value }: { label: string; value: ReactNode }) => (
  <div className="flex justify-between gap-2">
    <span className="text-muted-foreground">{label}</span>
    <span className="text-right">{value}</span>
  </div>
);

interface SemanticSummaryProps {
  projectId: string;
  floorId: string;
}

export const SemanticSummary = ({ projectId, floorId }: SemanticSummaryProps) => {
  const { data: doc, isLoading, isError } = useOutputDocument(projectId, floorId);
  const apply = useApplyEdit(projectId, floorId);

  if (isLoading) return <p className="p-4 text-sm text-muted-foreground">Loading summary…</p>;
  if (isError || !doc)
    return <p className="p-4 text-sm text-muted-foreground">No analysis available.</p>;

  const onApply = apply.mutate;
  const rooms = doc.elements.filter((e) => e.kind === 'room');
  const scaleKnown = doc.scale_px_per_m != null;
  const planAreaPx = doc.width * doc.height;
  const roomNames = Array.from(
    new Set(rooms.map((r) => r.label ?? r.type ?? r.id)),
  );

  return (
    <div className="space-y-5 p-4 text-sm">
      <BuildingSummary projectId={projectId} />

      <PricePanel projectId={projectId} floorId={floorId} />

      <Section title="Overview">
        <Row label="Building" value={doc.building_type ?? '-'} />
        <Row label="Floors" value={doc.floor_count ?? '-'} />
        <Row label="Elements" value={doc.elements.length} />
      </Section>

      <Section title={`Rooms (${rooms.length})`}>
        {rooms.length === 0 ? (
          <p className="text-muted-foreground">No rooms detected.</p>
        ) : (
          <ul className="divide-y divide-border/50">
            {rooms.map((r) => (
              <RoomRow
                key={r.id}
                room={r}
                scaleKnown={scaleKnown}
                planAreaPx={planAreaPx}
              />
            ))}
          </ul>
        )}
        {!scaleKnown && rooms.length > 0 && (
          <p className="pt-1 text-xs text-muted-foreground">
            Sizes shown as % of plan area — calibrate scale for m².
          </p>
        )}
      </Section>

      <Section title={`Adjacencies (${doc.adjacency.length})`}>
        {doc.adjacency.length > 0 && (
          <AdjacencyGraph adjacency={doc.adjacency} roomNames={roomNames} />
        )}
        <AdjacencyEditor adjacency={doc.adjacency} roomNames={roomNames} onApply={onApply} />
      </Section>

      {doc.notes && (
        <Section title="Notes">
          <p className="text-muted-foreground">{doc.notes}</p>
        </Section>
      )}
    </div>
  );
};
