import { useQueries } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { Floor } from '@/features/projects';

// Fetch several floors' output documents at once (shares the ['output', …] cache
// with useOutputDocument). Used by the building-level summary, which needs each
// floor's full Document — the project manifest keeps floors light (no polygons).
export const useOutputDocuments = (projectId: string, floorIds: string[]) =>
  useQueries({
    queries: floorIds.map((floorId) => ({
      queryKey: ['output', projectId, floorId],
      queryFn: () => api.get<Floor>(`/projects/${projectId}/output/${floorId}`),
    })),
  });
