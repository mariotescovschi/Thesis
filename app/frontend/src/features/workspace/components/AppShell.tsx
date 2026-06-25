import { useCallback, useRef, useState } from 'react';
import { CenterStage } from '@/features/viewer';
import { SearchView } from '@/features/search';
import { useWorkspaceStore } from '../store/workspaceStore';
import { Sidebar } from './Sidebar';
import { RightPanel } from './RightPanel';

export const AppShell = () => {
  const projectId = useWorkspaceStore((s) => s.activeProjectId);
  const activeFile = useWorkspaceStore((s) => s.activeFile);
  const setActiveFile = useWorkspaceStore((s) => s.setActiveFile);
  const setActiveProjectId = useWorkspaceStore((s) => s.setActiveProjectId);
  const mode = useWorkspaceStore((s) => s.mode);
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [collapsed, setCollapsed] = useState(false);
  const dragging = useRef(false);

  const onMouseDown = useCallback(() => {
    dragging.current = true;
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      setSidebarWidth(Math.max(180, Math.min(480, e.clientX)));
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, []);

  const cols = collapsed
    ? 'auto minmax(0, 1fr) auto'
    : `${sidebarWidth}px auto minmax(0, 1fr) auto`;

  return (
    <div className="grid h-full w-full overflow-hidden" style={{ gridTemplateColumns: cols, gridTemplateRows: 'minmax(0, 1fr)' }}>
      <Sidebar collapsed={collapsed} onToggleCollapse={() => setCollapsed((c) => !c)} />
      {!collapsed && (
        <div
          onMouseDown={onMouseDown}
          className="w-1 cursor-col-resize bg-border hover:bg-primary/50 transition-colors"
        />
      )}
      <main className="min-w-0 overflow-hidden bg-background">
        {mode === 'search' ? (
          <SearchView
            onOpenResult={(pid, floorId) => {
              setActiveProjectId(pid);
              setActiveFile({ kind: 'output', floorId });
            }}
          />
        ) : (
          <CenterStage
            projectId={projectId}
            activeFile={activeFile}
            onSelectFloor={(floorId) =>
              setActiveFile({ kind: activeFile?.kind ?? 'output', floorId })
            }
          />
        )}
      </main>
      <RightPanel />
    </div>
  );
};
