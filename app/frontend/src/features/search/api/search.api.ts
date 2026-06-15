import { api } from '@/shared/api/client';
import type { SearchResponse } from '../types/search';

export const searchApi = {
  query: (query: string, topK = 20) =>
    api.post<SearchResponse>('/search', { query, top_k: topK }),
};
