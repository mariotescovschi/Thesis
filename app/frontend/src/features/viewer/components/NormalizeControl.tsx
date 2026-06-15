import { useState } from 'react';
import { Wand2, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/shared/lib/cn';
import { useEditorStore } from '../store/editorStore';
import { useApplyEdits } from '../hooks/actions/useApplyEdits';
import { useNormalize } from '../hooks/actions/useNormalize';

interface NormalizeControlProps {
  projectId: string;
  floorId: string;
}

const LEVELS = [
  { level: 1, label: 'Light', hint: 'Snap edges, merge near-duplicate corners' },
  { level: 2, label: 'Medium', hint: 'Light + weld room corners to walls' },
  { level: 3, label: 'Hard', hint: 'Medium + remove room overlaps' },
] as const;

/**
 * Toolbar control for the on-demand Normalize pass. Picking a level (1..3) loads a
 * non-destructive amber preview onto the canvas; Apply commits it to the overlay
 * via the batch endpoint, Discard clears it. The pipeline base is never touched.
 */
export const NormalizeControl = ({ projectId, floorId }: NormalizeControlProps) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const { preview: runPreview, level, proposed, count, isPending } = useNormalize(projectId, floorId);
  const preview = useEditorStore((s) => s.preview);
  const clearPreview = useEditorStore((s) => s.clearPreview);
  const apply = useApplyEdits(projectId, floorId);

  const hasProposal = proposed && preview.length > 0;
  const isClean = proposed && !isPending && count === 0;

  const onApply = async () => {
    setBusy(true);
    try {
      await apply.mutateAsync(preview);
      clearPreview();
      setOpen(false);
      toast.success(`Normalized ${preview.length} element${preview.length > 1 ? 's' : ''}`);
    } catch (e) {
      toast.error('Could not normalize', { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Normalize geometry"
        className="flex items-center gap-1.5 rounded-md border border-border bg-card/90 px-2.5 py-1.5 text-xs text-foreground backdrop-blur transition-colors hover:bg-card"
      >
        <Wand2 className="size-3.5" />
        Normalize
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            role="menu"
            className="absolute right-0 top-full z-20 mt-1 w-64 overflow-hidden rounded-md border border-border bg-popover p-1 shadow-lg"
          >
            {LEVELS.map((l) => (
              <button
                key={l.level}
                role="menuitemradio"
                aria-checked={level === l.level}
                onClick={() => runPreview(l.level)}
                disabled={isPending}
                className={cn(
                  'block w-full rounded px-3 py-2 text-left transition-colors hover:bg-muted disabled:opacity-50',
                  level === l.level && 'bg-primary/10',
                )}
              >
                <span className="text-xs font-medium text-popover-foreground">
                  {l.level}. {l.label}
                </span>
                <span className="block text-[11px] text-muted-foreground">{l.hint}</span>
              </button>
            ))}

            {isPending && <p className="px-3 py-2 text-[11px] text-muted-foreground">Computing…</p>}
            {isClean && (
              <p className="px-3 py-2 text-[11px] text-muted-foreground">
                Nothing to clean up at this level.
              </p>
            )}
            {hasProposal && (
              <div className="mt-1 border-t border-border p-2">
                <p className="mb-2 px-1 text-[11px] text-muted-foreground">
                  {preview.length} change{preview.length > 1 ? 's' : ''} previewed on the canvas
                  (amber). Apply writes the overlay.
                </p>
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
            )}
          </div>
        </>
      )}
    </div>
  );
};
