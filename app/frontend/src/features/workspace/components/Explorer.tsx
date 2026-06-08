import { type ReactNode, useState } from 'react';
import { ChevronDown, ChevronRight, Plus } from 'lucide-react';
import { AddFloorPlanModal } from '@/features/floorplans';
import { AnalyzeButton, StatusChip } from '@/features/analysis';
import { useProject } from '@/features/projects';
import { useWorkspaceStore } from '../store/workspaceStore';
import { FileRow } from './FileRow';
import { FileIcon } from './FileIcon';

interface FolderProps {
  label: string;
  icon: ReactNode;
  empty: string;
  action?: ReactNode;
  children?: ReactNode;
}

const Folder = ({ label, icon, empty, action, children }: FolderProps) => {
  const [open, setOpen] = useState(true);
  const isEmpty = !children || (Array.isArray(children) && children.length === 0);
  return (
    <div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center gap-1.5 rounded-md px-1 py-1 text-sm font-medium uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
        >
          {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          {icon}
          {label}
        </button>
        {action}
      </div>
      {open && (
        <div className="pl-2">
          {isEmpty ? (
            <p className="px-2 py-1.5 text-sm text-muted-foreground/70">{empty}</p>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
};

export const Explorer = () => {
  const projectId = useWorkspaceStore((s) => s.activeProjectId);
  const activeFile = useWorkspaceStore((s) => s.activeFile);
  const setActiveFile = useWorkspaceStore((s) => s.setActiveFile);
  const [addOpen, setAddOpen] = useState(false);
  const { data: project } = useProject(projectId);

  if (!projectId) return null;
  const floors = project?.floors ?? [];
  const analyzed = floors.filter((f) => f.status === 'done');

  return (
    <div className="mt-2 space-y-1 border-t border-border pt-2">
      <div className="pb-1">
        <AnalyzeButton projectId={projectId} />
      </div>
      <Folder
        label="input"
        icon={<FileIcon filename="input/" />}
        empty="No floor plans yet"
        action={
          <button
            onClick={() => setAddOpen(true)}
            aria-label="Add floor plan"
            className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <Plus className="size-3.5" />
          </button>
        }
      >
        {floors.map((f) => (
          <FileRow
            key={f.id}
            icon={<FileIcon filename={f.filename} />}
            label={f.name}
            active={activeFile?.kind === 'input' && activeFile.floorId === f.id}
            onClick={() => setActiveFile({ kind: 'input', floorId: f.id })}
            trailing={<StatusChip status={f.status} />}
          />
        ))}
      </Folder>

      <Folder label="output" icon={<FileIcon filename="output/" />} empty="Empty until analyzed">
        {analyzed.map((f) => (
          <FileRow
            key={f.id}
            icon={<FileIcon filename={`${f.name}.json`} />}
            label={`${f.name}.json`}
            active={activeFile?.kind === 'output' && activeFile.floorId === f.id}
            onClick={() => setActiveFile({ kind: 'output', floorId: f.id })}
          />
        ))}
      </Folder>

      <AddFloorPlanModal projectId={projectId} open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
};
