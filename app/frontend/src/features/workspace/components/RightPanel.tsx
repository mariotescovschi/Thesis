import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import { ChatPanel } from '@/features/chat';
import { Button } from '@/shared/components/ui/button';
import { useWorkspaceStore } from '../store/workspaceStore';

export const RightPanel = () => {
  const open = useWorkspaceStore((s) => s.rightPanelOpen);
  const toggle = useWorkspaceStore((s) => s.toggleRightPanel);
  const projectId = useWorkspaceStore((s) => s.activeProjectId);
  const activeFile = useWorkspaceStore((s) => s.activeFile);

  if (!open) {
    return (
      <div className="flex w-10 flex-col items-center border-l border-border bg-card/40 py-3">
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Open panel">
          <PanelRightOpen />
        </Button>
      </div>
    );
  }

  return (
    <aside className="flex h-full w-[340px] flex-col overflow-hidden border-l border-border bg-card/40">
      <header className="flex h-11 items-center justify-end border-b border-border px-3">
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Collapse panel">
          <PanelRightClose />
        </Button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <ChatPanel projectId={projectId} activeFile={activeFile} />
      </div>
    </aside>
  );
};
