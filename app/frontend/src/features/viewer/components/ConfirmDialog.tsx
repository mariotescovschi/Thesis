import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDialog = ({
  open,
  title,
  description,
  confirmLabel = 'Delete',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) => (
  <Dialog open={open} onOpenChange={(v) => !v && onCancel()}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        {description && <DialogDescription>{description}</DialogDescription>}
      </DialogHeader>
      <DialogFooter>
        <button
          onClick={onCancel}
          className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:bg-accent"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="rounded-md bg-destructive px-3 py-1.5 text-sm text-destructive-foreground transition-colors hover:bg-destructive/90"
        >
          {confirmLabel}
        </button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);
