import { api } from '@/shared/api/client';
import type { Project } from '@/features/projects';

export const analysisApi = {
  analyze: (projectId: string, force = false) =>
    api.post<Project>(`/projects/${projectId}/analyze${force ? '?force=true' : ''}`),
};
