import { Check, CircleDashed, Loader2, TriangleAlert } from 'lucide-react';
import type { FloorStatus } from '@/features/projects';

export const StatusChip = ({ status }: { status: FloorStatus }) => {
  if (status === 'done')
    return <Check className="size-3.5 text-emerald-500" aria-label="Analyzed" />;
  if (status === 'running')
    return <Loader2 className="size-3.5 animate-spin text-primary" aria-label="Analyzing" />;
  if (status === 'error')
    return <TriangleAlert className="size-3.5 text-destructive" aria-label="Failed" />;
  return <CircleDashed className="size-3.5 text-muted-foreground/50" aria-label="Pending" />;
};
