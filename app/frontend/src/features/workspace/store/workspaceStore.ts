import { create } from 'zustand';

export type ActiveFile = { kind: 'input' | 'output'; floorId: string } | null;

interface WorkspaceState {
  activeProjectId: string | null;
  activeFile: ActiveFile;
  rightPanelOpen: boolean;
  setActiveProjectId: (id: string | null) => void;
  setActiveFile: (file: ActiveFile) => void;
  toggleRightPanel: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeProjectId: null,
  activeFile: null,
  rightPanelOpen: true,
  // Switching projects clears the focused file.
  setActiveProjectId: (id) => set({ activeProjectId: id, activeFile: null }),
  setActiveFile: (file) => set({ activeFile: file }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
}));
