import { useState } from 'react';
import { Check, X, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { useApplyEdits, useEditorStore, useOutputDocument, type EditCommand } from '@/features/viewer';

interface ProposedEditsProps {
  projectId: string;
  floorId: string;
}

/** Resolve element_id to a friendly name using the document. */
const useFriendlyName = (projectId: string, floorId: string) => {
  const { data: doc } = useOutputDocument(projectId, floorId);
  return (id: string) => {
    const el = doc?.elements.find((e) => e.id === id);
    if (!el) return id;
    return el.label || el.type || el.kind;
  };
};

const describe = (cmd: EditCommand, name: (id: string) => string): string => {
  switch (cmd.op) {
    case 'set_label':
      return `Label ${name(cmd.element_id)} → "${cmd.label}"`;
    case 'set_type':
      return `Type ${name(cmd.element_id)} → "${cmd.type}"`;
    case 'set_area_m2':
      return `Area ${name(cmd.element_id)} → ${cmd.area_m2.toFixed(2)} m²`;
    case 'add_adjacency':
      return `Link ${cmd.from} ↔ ${cmd.to}`;
    case 'remove_adjacency':
      return `Unlink ${cmd.from} ↔ ${cmd.to}`;
    case 'delete_element':
      return `Delete ${name(cmd.element_id)}`;
    case 'merge_rooms':
      return `Merge ${cmd.element_ids.map(name).join(', ')}`;
    case 'split_room':
      return `Split ${name(cmd.element_id)} with a wall`;
    case 'add_wall':
      return 'Add a wall';
    case 'move_element':
      return `Move ${name(cmd.element_id)}`;
    case 'set_scale':
      return `Set scale → ${cmd.scale_px_per_m.toFixed(1)} px/m`;
    case 'add_annotation':
      return `Add pin "${cmd.name}"`;
    case 'update_annotation':
      return `Update pin ${cmd.id}`;
    case 'delete_annotation':
      return `Delete pin ${cmd.id}`;
    default:
      return 'Edit';
  }
};

/** Lists chat-proposed commands and applies them to the overlay on confirm (Q7=A). */
export const ProposedEdits = ({ projectId, floorId }: ProposedEditsProps) => {
  const preview = useEditorStore((s) => s.preview);
  const clearPreview = useEditorStore((s) => s.clearPreview);
  const apply = useApplyEdits(projectId, floorId);
  const [busy, setBusy] = useState(false);
  const name = useFriendlyName(projectId, floorId);

  if (preview.length === 0) return null;

  const onApply = async () => {
    setBusy(true);
    try {
      // Atomic: the backend applies all commands or none, so a contradictory set
      // (e.g. delete + split the same room) fails cleanly without corrupting the plan.
      await apply.mutateAsync(preview);
      clearPreview();
      toast.success(`Applied ${preview.length} edit${preview.length > 1 ? 's' : ''}`);
    } catch (e) {
      toast.error('Could not apply these edits', {
        description: (e as Error).message,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="m-3 rounded-lg border border-primary/40 bg-primary/5 p-3 text-sm">
      <div className="mb-2 flex items-center gap-2 text-primary">
        <Sparkles className="size-4" />
        <span className="font-medium">Proposed edits ({preview.length})</span>
      </div>
      <ul className="mb-3 space-y-1 text-xs text-foreground">
        {preview.map((cmd, i) => (
          <li key={i} className="truncate">
            • {describe(cmd, name)}
          </li>
        ))}
      </ul>
      <p className="mb-2 text-xs text-muted-foreground">Highlighted on the canvas in amber.</p>
      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={onApply}
          className="flex flex-1 items-center justify-center gap-1 rounded-md bg-primary px-2 py-1.5 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <Check className="size-3.5" />
          {busy ? 'Applying…' : 'Apply'}
        </button>
        <button
          disabled={busy}
          onClick={clearPreview}
          className="flex items-center justify-center gap-1 rounded-md border border-border px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <X className="size-3.5" />
          Discard
        </button>
      </div>
    </div>
  );
};
