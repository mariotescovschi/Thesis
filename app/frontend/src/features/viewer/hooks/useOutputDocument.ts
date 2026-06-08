import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { Floor } from '@/features/projects';

export const useOutputDocument = (projectId: string, floorId: string) =>
  useQuery({
    queryKey: ['output', projectId, floorId],
    queryFn: () => api.get<Floor>(`/projects/${projectId}/output/${floorId}`),
  });
