import { create } from 'zustand';
import type { Floor } from '@/features/projects';
import type { EditCommand } from '../types/command';

export type EditorTool = 'select' | 'move' | 'vertex' | 'wall' | 'split' | 'annotate' | 'calibrate';

// History slice captured for optimistic rollback (useApplyEdit / useRevertEdits).
export interface EditorSnapshot {
  doc: Floor | null;
  past: Floor[];
  future: Floor[];
  dirty: boolean;
}

interface EditorState extends EditorSnapshot {
  selection: string | null;
  tool: EditorTool;
  preview: EditCommand[]; // chat-proposed, non-destructive until applied
  setDoc: (doc: Floor | null) => void;
  setSelection: (id: string | null) => void;
  setTool: (tool: EditorTool) => void;
  setDirty: (dirty: boolean) => void;
  setPreview: (commands: EditCommand[]) => void;
  clearPreview: () => void;
  commit: (next: Floor) => void; // push current onto past, swap in next, clear redo
  undo: () => void;
  redo: () => void;
  snapshot: () => EditorSnapshot;
  restore: (snap: EditorSnapshot) => void;
  reset: () => void;
}

const EMPTY: EditorSnapshot = { doc: null, past: [], future: [], dirty: false };

export const useEditorStore = create<EditorState>((set, get) => ({
  ...EMPTY,
  selection: null,
  tool: 'select',
  preview: [],
  setDoc: (doc) => set({ doc }),
  setSelection: (selection) => set({ selection }),
  setTool: (tool) => set({ tool }),
  setDirty: (dirty) => set({ dirty }),
  setPreview: (preview) => set({ preview }),
  clearPreview: () => set({ preview: [] }),
  commit: (next) => {
    const { doc, past } = get();
    set({ doc: next, past: doc ? [...past, doc] : past, future: [], dirty: true });
  },
  undo: () => {
    const { doc, past, future } = get();
    const prev = past[past.length - 1];
    if (!prev) return;
    set({
      doc: prev,
      past: past.slice(0, -1),
      future: doc ? [doc, ...future] : future,
      dirty: true,
    });
  },
  redo: () => {
    const { doc, past, future } = get();
    const [next, ...rest] = future;
    if (!next) return;
    set({ doc: next, past: doc ? [...past, doc] : past, future: rest, dirty: true });
  },
  snapshot: () => {
    const { doc, past, future, dirty } = get();
    return { doc, past, future, dirty };
  },
  restore: (snap) => set({ ...snap }),
  reset: () => set({ ...EMPTY, selection: null, tool: 'select', preview: [] }),
}));
