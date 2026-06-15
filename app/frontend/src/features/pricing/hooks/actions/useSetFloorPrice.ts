import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectKeys } from '@/features/projects';
import { pricingApi } from '../../api/pricing.api';
import { priceKeys } from '../queries/usePriceEstimate';

/** Set a floor's asking price, then refresh the project detail + its estimate. */
export const useSetFloorPrice = (projectId: string, floorId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (price: number | null) => pricingApi.setFloorPrice(projectId, floorId, price),
    onSuccess: (project) => {
      qc.setQueryData(projectKeys.detail(project.id), project);
      qc.invalidateQueries({ queryKey: priceKeys.estimate(projectId, floorId) });
    },
  });
};
