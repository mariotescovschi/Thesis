import { api } from '@/shared/api/client';
import type { Project, ProjectSummary } from '../types/project';

export interface CreateProjectInput {
  name: string;
  type: string;
  location?: string;
}

export const projectsApi = {
  list: () => api.get<ProjectSummary[]>('/projects'),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (input: CreateProjectInput) => api.post<Project>('/projects', input),
};
