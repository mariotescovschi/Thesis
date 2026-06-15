import { create } from 'zustand';

export type ActiveFile = { kind: 'input' | 'output'; floorId: string } | null;
export type WorkspaceMode = 'workspace' | 'search';

interface WorkspaceState {
  activeProjectId: string | null;
  activeFile: ActiveFile;
  mode: WorkspaceMode;
  rightPanelOpen: boolean;
  setActiveProjectId: (id: string | null) => void;
  setActiveFile: (file: ActiveFile) => void;
  setMode: (mode: WorkspaceMode) => void;
  toggleRightPanel: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeProjectId: null,
  activeFile: null,
  mode: 'workspace',
  rightPanelOpen: true,
  // Switching projects clears the focused file and leaves search mode.
  setActiveProjectId: (id) => set({ activeProjectId: id, activeFile: null, mode: 'workspace' }),
  setActiveFile: (file) => set({ activeFile: file, mode: 'workspace' }),
  setMode: (mode) => set({ mode }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
}));
