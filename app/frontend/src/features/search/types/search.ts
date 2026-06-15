// Mirrors the backend search service response (services/search.py: search()).

export interface SearchResult {
  project_id: string;
  floor_id: string;
  project_name: string;
  floor_name: string;
  price: number | null;
  currency: string;
  description?: string | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  filters: Record<string, number | string>;
  semantic: boolean;
  results: SearchResult[];
}
