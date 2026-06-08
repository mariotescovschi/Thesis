import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectKeys } from '@/features/projects';
import { floorplansApi, type FloorUploadItem } from '../api/floorplans.api';

export const useUploadFloors = (projectId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: FloorUploadItem[]) => floorplansApi.upload(projectId, items),
    onSuccess: (project) => {
      qc.setQueryData(projectKeys.detail(projectId), project);
      qc.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
};
