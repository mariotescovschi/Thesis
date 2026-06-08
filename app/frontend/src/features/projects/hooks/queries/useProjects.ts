import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '../../api/projectsApi';

export const projectKeys = {
  all: ['projects'] as const,
  detail: (id: string) => ['projects', id] as const,
};

export const useProjects = () =>
  useQuery({ queryKey: projectKeys.all, queryFn: projectsApi.list });

export const useProject = (id: string | null) =>
  useQuery({
    queryKey: projectKeys.detail(id ?? '_none'),
    queryFn: () => projectsApi.get(id as string),
    enabled: !!id,
  });
