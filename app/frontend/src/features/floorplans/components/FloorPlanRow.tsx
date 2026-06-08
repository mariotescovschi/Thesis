import { X } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';

export interface FloorDraft {
  id: string;
  file: File;
  previewUrl: string;
  name: string;
  description: string;
}

interface FloorPlanRowProps {
  draft: FloorDraft;
  onChange: (patch: Partial<FloorDraft>) => void;
  onRemove: () => void;
}

export const FloorPlanRow = ({ draft, onChange, onRemove }: FloorPlanRowProps) => (
  <div className="flex gap-3 rounded-lg border border-border p-2">
    <img
      src={draft.previewUrl}
      alt=""
      className="size-16 shrink-0 rounded bg-muted object-cover"
    />
    <div className="flex flex-1 flex-col gap-1.5">
      <Input
        value={draft.name}
        onChange={(e) => onChange({ name: e.target.value })}
        placeholder="Floor name"
        aria-invalid={!draft.name.trim()}
      />
      <Input
        value={draft.description}
        onChange={(e) => onChange({ description: e.target.value })}
        placeholder="Description (optional)"
      />
    </div>
    <Button variant="ghost" size="icon" onClick={onRemove} aria-label="Remove floor plan">
      <X />
    </Button>
  </div>
);
