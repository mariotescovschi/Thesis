import { BASE, ApiError } from '@/shared/api/client';
import type { Floor } from '@/features/projects';
import type { EditCommand } from '../types/command';

// Local request helper reusing the shared base URL + `{ data }/{ error }` envelope
// convention (the shared client exposes get/post only; edits need PATCH/DELETE).
interface Envelope<T> {
  data?: T;
  error?: { message: string; code?: string };
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  const body = (await res.json().catch(() => null)) as Envelope<T> | null;
  if (!res.ok || !body || body.error) {
    throw new ApiError(body?.error?.message ?? res.statusText, body?.error?.code, res.status);
  }
  return body.data as T;
}

export const editApi = {
  applyEdit: (projectId: string, floorId: string, command: EditCommand) =>
    request<Floor>(`/projects/${projectId}/output/${floorId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    }),
  applyEdits: (projectId: string, floorId: string, commands: EditCommand[]) =>
    request<Floor>(`/projects/${projectId}/output/${floorId}/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commands }),
    }),
  revertEdits: (projectId: string, floorId: string) =>
    request<Floor>(`/projects/${projectId}/output/${floorId}/edits`, { method: 'DELETE' }),
};
