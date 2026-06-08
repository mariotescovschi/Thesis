import { useRef, useState } from 'react';
import { ImagePlus, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/shared/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import { useUploadFloors } from '../hooks/useUploadFloors';
import { FloorPlanRow, type FloorDraft } from './FloorPlanRow';

let seq = 0;

interface AddFloorPlanModalProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const AddFloorPlanModal = ({ projectId, open, onOpenChange }: AddFloorPlanModalProps) => {
  const [drafts, setDrafts] = useState<FloorDraft[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const upload = useUploadFloors(projectId);

  const addFiles = (files: FileList | null) => {
    if (!files) return;
    const next = Array.from(files).map((file) => ({
      id: `d${seq++}`,
      file,
      previewUrl: URL.createObjectURL(file),
      name: file.name.replace(/\.[^.]+$/, ''),
      description: '',
    }));
    setDrafts((d) => [...d, ...next]);
  };

  const reset = () =>
    setDrafts((d) => {
      d.forEach((x) => URL.revokeObjectURL(x.previewUrl));
      return [];
    });

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const removeAt = (id: string) =>
    setDrafts((d) => {
      const target = d.find((x) => x.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return d.filter((x) => x.id !== id);
    });

  const patchAt = (id: string, patch: Partial<FloorDraft>) =>
    setDrafts((d) => d.map((x) => (x.id === id ? { ...x, ...patch } : x)));

  const valid = drafts.length > 0 && drafts.every((d) => d.name.trim());

  const submit = () =>
    upload.mutate(
      drafts.map((d) => ({
        file: d.file,
        name: d.name.trim(),
        description: d.description.trim() || undefined,
      })),
      {
        onSuccess: () => {
          toast.success(`Added ${drafts.length} floor plan${drafts.length > 1 ? 's' : ''}`);
          reset();
          onOpenChange(false);
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : 'Upload failed'),
      },
    );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Add Floor Plan</DialogTitle>
          <DialogDescription>
            {drafts.length === 0
              ? 'Upload one or more floor-plan images.'
              : `${drafts.length} floor plan${drafts.length > 1 ? 's' : ''}`}
          </DialogDescription>
        </DialogHeader>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = '';
          }}
        />

        {drafts.length === 0 ? (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-10 text-sm text-muted-foreground transition-colors hover:border-primary/60 hover:text-foreground"
          >
            <ImagePlus className="size-6" />
            Choose images
          </button>
        ) : (
          <div className="flex max-h-[50vh] flex-col gap-2 overflow-y-auto pr-1">
            {drafts.map((d) => (
              <FloorPlanRow
                key={d.id}
                draft={d}
                onChange={(p) => patchAt(d.id, p)}
                onRemove={() => removeAt(d.id)}
              />
            ))}
            <Button
              variant="outline"
              size="sm"
              className="self-start"
              onClick={() => fileRef.current?.click()}
            >
              <Plus /> Add more
            </Button>
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!valid || upload.isPending} onClick={submit}>
            {upload.isPending
              ? 'Uploading…'
              : `Create ${drafts.length || ''} ${drafts.length === 1 ? 'Floor Plan' : 'Floor Plans'}`.replace(
                  '  ',
                  ' ',
                )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
