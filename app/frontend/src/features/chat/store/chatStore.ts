import { create } from 'zustand';
import type { RejectedCommand } from '../api/chat.api';

export interface ChatTurn {
  role: 'user' | 'assistant';
  text: string;
}

interface ChatState {
  // Current in-memory transcript. Lives in the store (not component state) so it
  // survives switching the Overview/Chat tabs; cleared explicitly via newChat().
  messages: ChatTurn[];
  // Element IDs added to chat context via shift+click on canvas.
  contextElementIds: string[];
  // Commands the backend rejected on the last turn (with reasons) — surfaced in
  // the UI instead of being silently dropped.
  rejected: RejectedCommand[];
  pushTurn: (turn: ChatTurn) => void;
  toggleContextElement: (id: string) => void;
  setRejected: (rejected: RejectedCommand[]) => void;
  newChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  contextElementIds: [],
  rejected: [],
  pushTurn: (turn) => set((s) => ({ messages: [...s.messages, turn] })),
  toggleContextElement: (id) =>
    set((s) => ({
      contextElementIds: s.contextElementIds.includes(id)
        ? s.contextElementIds.filter((x) => x !== id)
        : [...s.contextElementIds, id],
    })),
  setRejected: (rejected) => set({ rejected }),
  newChat: () => set({ messages: [], contextElementIds: [], rejected: [] }),
}));
