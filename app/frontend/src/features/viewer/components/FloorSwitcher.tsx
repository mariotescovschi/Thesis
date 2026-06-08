import { Layers } from 'lucide-react';
import type { FloorStatus } from '@/features/projects';
import { cn } from '@/shared/lib/cn';

interface FloorTab {
  id: string;
  name: string;
  status: FloorStatus;
}

interface FloorSwitcherProps {
  floors: FloorTab[];
  activeFloorId: string;
  onSelect: (floorId: string) => void;
}

const STATUS_DOT: Record<FloorStatus, string> = {
  pending: 'bg-muted-foreground/40',
  running: 'bg-amber-400',
  done: 'bg-emerald-400',
  error: 'bg-destructive',
};

/** Horizontal floor tabs shown for multi-floor projects. */
export const FloorSwitcher = ({ floors, activeFloorId, onSelect }: FloorSwitcherProps) => (
  <div className="flex items-center gap-1 border-b border-border bg-card/40 px-2 py-1">
    <Layers className="mx-1 size-3.5 text-muted-foreground" />
    {floors.map((f) => (
      <button
        key={f.id}
        onClick={() => onSelect(f.id)}
        aria-current={f.id === activeFloorId}
        className={cn(
          'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors',
          f.id === activeFloorId
            ? 'bg-primary/15 text-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <span className={cn('size-1.5 rounded-full', STATUS_DOT[f.status])} />
        {f.name}
      </button>
    ))}
  </div>
);
