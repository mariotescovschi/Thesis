import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '../../api/projectsApi';
import { projectKeys } from '../queries/useProjects';

export const useCreateProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: projectKeys.all });
      qc.setQueryData(projectKeys.detail(project.id), project);
    },
  });
};
