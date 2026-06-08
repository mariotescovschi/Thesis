import { api } from '@/shared/api/client';
import type { EditCommand } from '@/features/viewer';

export interface ChatRequest {
  floor_id: string;
  message: string;
  pin_ids: string[];
  element_ids: string[];
  history: { role: string; text: string }[];
}

export interface ChatResponse {
  answer: string;
  proposed_commands: EditCommand[];
}

export const chatApi = {
  send: (projectId: string, body: ChatRequest) =>
    api.post<ChatResponse>(`/projects/${projectId}/chat`, body),
};
