import { type ReactNode } from 'react';
import { Building2, MousePointerClick } from 'lucide-react';
import { useProject } from '@/features/projects';
import { ImageViewer } from './ImageViewer';
import { OutputCanvas } from './OutputCanvas';
import { FloorSwitcher } from './FloorSwitcher';

// Kept prop-driven (not store-coupled) so the viewer feature has no dependency on workspace.
type ActiveFile = { kind: 'input' | 'output'; floorId: string } | null;

interface CenterStageProps {
  projectId: string | null;
  activeFile: ActiveFile;
  onSelectFloor?: (floorId: string) => void;
}

const EmptyState = ({
  icon,
  title,
  sub,
}: {
  icon: ReactNode;
  title: string;
  sub: string;
}) => (
  <div className="stage-grain flex h-full flex-col items-center justify-center p-8 text-center">
    <div className="mb-3 text-muted-foreground/60">{icon}</div>
    <h2 className="font-display text-xl font-semibold tracking-tight">{title}</h2>
    <p className="mt-1 max-w-sm text-sm text-muted-foreground">{sub}</p>
  </div>
);

export const CenterStage = ({ projectId, activeFile, onSelectFloor }: CenterStageProps) => {
  const { data: project } = useProject(projectId);

  if (!projectId)
    return (
      <EmptyState
        icon={<Building2 className="size-9" />}
        title="Mappa"
        sub="Create a project and add floor plans to begin. Geometry runs locally; semantics on demand."
      />
    );

  if (!activeFile)
    return (
      <EmptyState
        icon={<MousePointerClick className="size-9" />}
        title="Nothing open"
        sub="Pick a floor plan from the explorer to view its image, or an analyzed result to inspect the geometry."
      />
    );

  const floors = project?.floors ?? [];

  return (
    <div className="flex h-full flex-col bg-background">
      {floors.length > 1 && onSelectFloor && (
        <FloorSwitcher
          floors={floors.map((f) => ({ id: f.id, name: f.name, status: f.status }))}
          activeFloorId={activeFile.floorId}
          onSelect={onSelectFloor}
        />
      )}
      <div key={`${activeFile.kind}:${activeFile.floorId}`} className="min-h-0 flex-1">
        {activeFile.kind === 'input' ? (
          <ImageViewer projectId={projectId} floorId={activeFile.floorId} />
        ) : (
          <OutputCanvas projectId={projectId} floorId={activeFile.floorId} />
        )}
      </div>
    </div>
  );
};
