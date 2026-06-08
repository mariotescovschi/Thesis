import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import { useCreateProject } from '../hooks/actions/useCreateProject';
import { ProjectTypeModal } from './ProjectTypeModal';
import type { Project } from '../types/project';

const DEFAULT_LOCATION = '~/MappaProjects';

interface NewProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (project: Project) => void;
}

export const NewProjectModal = ({ open, onOpenChange, onCreated }: NewProjectModalProps) => {
  const [step, setStep] = useState<'details' | 'type'>('details');
  const [name, setName] = useState('');
  const [location, setLocation] = useState(DEFAULT_LOCATION);
  const create = useCreateProject();

  const reset = () => {
    setStep('details');
    setName('');
    setLocation(DEFAULT_LOCATION);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const handleConfirm = (type: string) => {
    create.mutate(
      { name: name.trim(), type, location: location.trim() || undefined },
      {
        onSuccess: (project) => {
          toast.success(`Created “${project.name}”`);
          reset();
          onOpenChange(false);
          onCreated(project);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : 'Could not create project'),
      },
    );
  };

  return (
    <>
      <Dialog open={open && step === 'details'} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>Give it a name and a place to live.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <label className="grid gap-1.5 text-sm">
              <span className="text-muted-foreground">Name</span>
              <Input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My house"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && name.trim()) setStep('type');
                }}
              />
            </label>
            <label className="grid gap-1.5 text-sm">
              <span className="text-muted-foreground">Save location</span>
              <Input value={location} onChange={(e) => setLocation(e.target.value)} />
            </label>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button disabled={!name.trim()} onClick={() => setStep('type')}>
              Next
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ProjectTypeModal
        open={open && step === 'type'}
        onOpenChange={handleOpenChange}
        onBack={() => setStep('details')}
        onConfirm={handleConfirm}
        pending={create.isPending}
      />
    </>
  );
};
