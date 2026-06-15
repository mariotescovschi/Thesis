import { api, BASE, ApiError } from '@/shared/api/client';
import type { Project } from '@/features/projects';
import type { PriceEstimate } from '../types/pricing';

// PATCH isn't on the shared client (get/post only), so reuse BASE + the envelope
// convention here, exactly like viewer/api/edit.api.ts.
interface Envelope<T> {
  data?: T;
  error?: { message: string; code?: string };
}

async function patchJson<T>(path: string, json: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(json),
  });
  const body = (await res.json().catch(() => null)) as Envelope<T> | null;
  if (!res.ok || !body || body.error) {
    throw new ApiError(body?.error?.message ?? res.statusText, body?.error?.code, res.status);
  }
  return body.data as T;
}

export const pricingApi = {
  estimate: (projectId: string, floorId: string) =>
    api.get<PriceEstimate>(`/projects/${projectId}/floors/${floorId}/price/estimate`),
  setFloorPrice: (projectId: string, floorId: string, price: number | null) =>
    patchJson<Project>(`/projects/${projectId}/floors/${floorId}/price`, { price }),
  setProjectPrice: (projectId: string, price: number | null, currency?: string) =>
    patchJson<Project>(`/projects/${projectId}/price`, { price, currency }),
};
