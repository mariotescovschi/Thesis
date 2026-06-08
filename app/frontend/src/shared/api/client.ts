/** Typed HTTP client. Unwraps the backend `{ data }` envelope; throws ApiError on `{ error }`. */
export const BASE = 'http://localhost:8000';

export class ApiError extends Error {
  readonly code?: string;
  readonly status?: number;
  constructor(message: string, code?: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

interface Envelope<T> {
  data?: T;
  error?: { message: string; code?: string };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  const body = (await res.json().catch(() => null)) as Envelope<T> | null;
  if (!res.ok || !body || body.error) {
    throw new ApiError(body?.error?.message ?? res.statusText, body?.error?.code, res.status);
  }
  return body.data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, json?: unknown) =>
    request<T>(path, {
      method: 'POST',
      headers: json !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: json !== undefined ? JSON.stringify(json) : undefined,
    }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: 'POST', body: form }),
};
