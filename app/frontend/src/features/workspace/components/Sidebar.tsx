import { useState } from 'react';
import { FolderPlus, Loader2, PanelLeftClose, PanelLeftOpen, Search, Settings } from 'lucide-react';
import { NewProjectModal, useProjects } from '@/features/projects';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/lib/cn';
import { useWorkspaceStore } from '../store/workspaceStore';
import { Explorer } from './Explorer';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar = ({ collapsed, onToggleCollapse }: SidebarProps) => {
  const [createOpen, setCreateOpen] = useState(false);
  const activeProjectId = useWorkspaceStore((s) => s.activeProjectId);
  const setActiveProjectId = useWorkspaceStore((s) => s.setActiveProjectId);
  const mode = useWorkspaceStore((s) => s.mode);
  const setMode = useWorkspaceStore((s) => s.setMode);
  const { data: projects, isLoading } = useProjects();

  if (collapsed) {
    return (
      <aside className="flex h-full w-14 flex-col items-center border-r border-border bg-card/40">
        <div className="flex h-12 items-center justify-center border-b border-border w-full">
          <button
            onClick={onToggleCollapse}
            className="group relative rounded hover:bg-accent"
          >
            <img src="/Logo.png" alt="Mappa" className="h-7 w-auto group-hover:opacity-0 transition-opacity duration-150" />
            <PanelLeftOpen className="size-5 absolute inset-0 m-auto opacity-0 group-hover:opacity-100 text-foreground transition-opacity duration-150" />
          </button>
        </div>
        <button
          onClick={() => { onToggleCollapse(); setCreateOpen(true); }}
          title="New project"
          className="mt-3 rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <FolderPlus className="size-5" />
        </button>
        <button
          onClick={() => setMode('search')}
          title="Search plans"
          className={cn(
            'mt-1 rounded-md p-2 hover:bg-accent hover:text-foreground',
            mode === 'search' ? 'text-foreground' : 'text-muted-foreground',
          )}
        >
          <Search className="size-5" />
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full flex-col border-r border-border bg-card/40">
      <header className="flex h-12 items-center justify-between border-b border-border px-3">
        <img src="/Logo.png" alt="Mappa" className="h-7 w-auto" />
        <button
          onClick={onToggleCollapse}
          className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <PanelLeftClose className="size-4" />
        </button>
      </header>

      <div className="p-3">
        <Button className="w-full" onClick={() => setCreateOpen(true)}>
          <FolderPlus /> New project
        </Button>
        <button
          onClick={() => setMode('search')}
          className={cn(
            'mt-2 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
            mode === 'search'
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:bg-accent/60',
          )}
        >
          <Search className="size-4" /> Search plans
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3">
        <p className="px-1 pb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Projects
        </p>

        {isLoading && (
          <div className="flex items-center gap-2 px-1 py-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Loading…
          </div>
        )}
        {!isLoading && projects?.length === 0 && (
          <p className="px-1 py-6 text-center text-xs text-muted-foreground/70">No projects yet</p>
        )}

        <ul className="space-y-0.5">
          {projects?.map((p) => (
            <li key={p.id}>
              <button
                onClick={() => setActiveProjectId(p.id)}
                className={cn(
                  'flex w-full flex-col rounded-md px-2 py-1.5 text-left transition-colors',
                  p.id === activeProjectId
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-accent/60',
                )}
              >
                <span className="truncate text-sm">{p.name}</span>
                <span className="text-[11px] text-muted-foreground">
                  {p.floor_count} {p.floor_count === 1 ? 'floor' : 'floors'}
                </span>
              </button>
              {p.id === activeProjectId && <Explorer />}
            </li>
          ))}
        </ul>
      </nav>

      <footer className="border-t border-border p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-muted-foreground"
          disabled
        >
          <Settings /> Settings
        </Button>
      </footer>

      <NewProjectModal
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(project) => setActiveProjectId(project.id)}
      />
    </aside>
  );
};
