// Mirrors the backend pricing service response (services/pricing.py: estimate()).

export type PriceVerdict = 'overpriced' | 'underpriced' | 'fair' | 'insufficient_data';

export interface PriceContribution {
  feature: string;
  pct: number; // signed % contribution to the estimate
}

export interface PriceComparable {
  project_id: string;
  floor_id: string;
  project_name: string;
  floor_name: string;
  price: number | null;
  similarity: number;
}

export interface PriceEstimate {
  available: boolean;
  reason?: string;
  currency: string;
  price: number | null; // current asking price (manifest)
  estimate?: number;
  verdict?: PriceVerdict;
  delta_pct?: number | null;
  contributions?: PriceContribution[];
  comparables?: PriceComparable[];
  sample_size?: number;
}
