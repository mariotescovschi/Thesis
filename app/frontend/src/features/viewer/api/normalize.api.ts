import { api } from '@/shared/api/client';
import type { EditCommand } from '../types/command';

// Proposes regularization edits for the current Document WITHOUT persisting.
// The backend returns move_element/delete_element commands; the caller loads them
// into the editor preview (amber ghost) and applies via the batch endpoint.
export const normalizeApi = {
  preview: (projectId: string, floorId: string, level: number) =>
    api.post<{ commands: EditCommand[] }>(
      `/projects/${projectId}/output/${floorId}/normalize`,
      { level },
    ),
};
