import { useState } from 'react';
import { Trash2, X } from 'lucide-react';
import type { Annotation } from '@/features/projects';
import type { EditCommand } from '../types/command';
import { ConfirmDialog } from './ConfirmDialog';

interface PinInspectorProps {
  pin: Annotation;
  onApply: (command: EditCommand) => void;
  onClose: () => void;
}

const inputCls =
  'rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground ' +
  'outline-none focus:border-primary';

export const PinInspector = ({ pin, onApply, onClose }: PinInspectorProps) => {
  const [name, setName] = useState(pin.name);
  const [note, setNote] = useState(pin.note ?? '');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const commitName = () => {
    const v = name.trim();
    if (v && v !== pin.name) onApply({ op: 'update_annotation', id: pin.id, name: v });
  };
  const commitNote = () => {
    if (note !== (pin.note ?? '')) onApply({ op: 'update_annotation', id: pin.id, note });
  };

  return (
    <>
      <div className="w-64 rounded-lg border border-border bg-card/95 p-3 shadow-lg backdrop-blur">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-foreground">Pin</span>
          <button
            onClick={onClose}
            aria-label="Close pin inspector"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="flex flex-col gap-2">
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted-foreground">Name</span>
            <input
              className={inputCls}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={commitName}
              onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted-foreground">Note</span>
            <textarea
              className={`${inputCls} min-h-16 resize-none`}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onBlur={commitNote}
              placeholder="Context for chat…"
            />
          </label>
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center justify-center gap-1.5 rounded-md border border-destructive/40 px-2 py-1 text-xs text-destructive transition-colors hover:bg-destructive/10"
          >
            <Trash2 className="size-3.5" />
            Delete pin
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete pin "${pin.name}"?`}
        description="This action cannot be undone."
        onConfirm={() => {
          onApply({ op: 'delete_annotation', id: pin.id });
          setConfirmDelete(false);
          onClose();
        }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
};
