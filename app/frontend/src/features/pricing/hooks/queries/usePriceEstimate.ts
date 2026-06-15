import { useQuery } from '@tanstack/react-query';
import { pricingApi } from '../../api/pricing.api';

export const priceKeys = {
  estimate: (projectId: string, floorId: string) =>
    ['price-estimate', projectId, floorId] as const,
};

export const usePriceEstimate = (projectId: string, floorId: string) =>
  useQuery({
    queryKey: priceKeys.estimate(projectId, floorId),
    queryFn: () => pricingApi.estimate(projectId, floorId),
  });
