import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectKeys } from '@/features/projects';
import { analysisApi } from '../api/analysis.api';

export const useAnalyze = (projectId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (force: boolean = false) => analysisApi.analyze(projectId, force),
    onSuccess: (project) => {
      qc.setQueryData(projectKeys.detail(projectId), project);
      qc.invalidateQueries({ queryKey: projectKeys.all });
      qc.invalidateQueries({ queryKey: ['output'] });
    },
  });
};
