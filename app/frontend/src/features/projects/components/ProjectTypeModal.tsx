import { useState } from 'react';
import { Boxes, GitCompare, ScanSearch } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import { cn } from '@/shared/lib/cn';

const TYPES = [
  {
    id: 'analysis',
    label: 'Analysis',
    desc: 'Extract geometry and semantics from existing floor plans.',
    icon: ScanSearch,
    enabled: true,
  },
  {
    id: 'generation',
    label: 'Generation',
    desc: 'Generate new plans from a brief.',
    icon: Boxes,
    enabled: false,
  },
  {
    id: 'comparison',
    label: 'Comparison',
    desc: 'Compare design variants side by side.',
    icon: GitCompare,
    enabled: false,
  },
];

interface ProjectTypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onBack: () => void;
  onConfirm: (type: string) => void;
  pending: boolean;
}

export const ProjectTypeModal = ({
  open,
  onOpenChange,
  onBack,
  onConfirm,
  pending,
}: ProjectTypeModalProps) => {
  const [selected, setSelected] = useState('analysis');
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Choose a workflow</DialogTitle>
          <DialogDescription>Analysis is available now. More are on the way.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-2">
          {TYPES.map((t) => (
            <button
              key={t.id}
              type="button"
              disabled={!t.enabled}
              onClick={() => setSelected(t.id)}
              className={cn(
                'flex items-start gap-3 rounded-lg border p-3 text-left transition-colors',
                t.enabled ? 'hover:border-primary/60' : 'cursor-not-allowed opacity-50',
                selected === t.id && t.enabled ? 'border-primary bg-primary/5' : 'border-border',
              )}
            >
              <t.icon className="mt-0.5 size-5 text-primary" />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-sm font-medium">
                  {t.label}
                  {!t.enabled && (
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                      Soon
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{t.desc}</p>
              </div>
            </button>
          ))}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onBack} disabled={pending}>
            Back
          </Button>
          <Button onClick={() => onConfirm(selected)} disabled={pending}>
            {pending ? 'Creating…' : 'Create project'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
