// Mirrors app/backend/document.py exactly (snake_case, no per-field renaming; rules §7).

export type FloorStatus = 'pending' | 'running' | 'done' | 'error';

export interface Element {
  id: string;
  kind: string; // room | wall | door | window | railing
  polygon: number[][];
  score?: number | null;
  label?: string | null;
  type?: string | null;
  area_m2?: number | null;
}

export interface Adjacency {
  from: string;
  to: string;
}

export interface Annotation {
  id: string;
  x: number; // image pixels
  y: number;
  name: string;
  note?: string | null;
}

export interface Floor {
  id: string;
  name: string;
  description?: string | null;
  filename: string;
  width: number;
  height: number;
  scale_px_per_m?: number | null;
  status: FloorStatus;
  elements: Element[];
  adjacency: Adjacency[];
  annotations: Annotation[];
  building_type?: string | null;
  floor_count?: number | null;
  notes?: string | null;
}

export interface ChatMessage {
  role: string;
  text: string;
}

export interface Link {
  type: string; // e.g. vertical_circulation
  from_floor: string;
  to_floor: string;
  via?: string | null; // stairs | ...
}

export interface Project {
  id: string;
  name: string;
  type: string;
  created: string;
  floors: Floor[];
  links: Link[];
  chat: ChatMessage[];
}

export interface ProjectSummary {
  id: string;
  name: string;
  type: string;
  created: string;
  floor_count: number;
}
